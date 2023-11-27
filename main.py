import asyncio
import os
import time
import aiosqlite
import uuid
import sanic
import aiohttp
import jinja2
import dotenv

app = sanic.Sanic("forum")

app.static('/assets/scripts/send.js', 'assets/scripts/send.js')


def utc_ms_to_dt(ms: int) -> str:
	return time.asctime(time.gmtime(ms // 1000))


@app.before_server_start
async def after_start(srv: sanic.Sanic, loop) -> None:
	srv.ctx.db = await aiosqlite.connect("messages.db")
	srv.ctx.db.row_factory = aiosqlite.Row
	cursor = await srv.ctx.db.cursor()
	await cursor.executescript("begin;"
							   "create table if not exists messages(message TEXT NOT NULL ,"
							   "thread_id TEXT NOT NULL,"
							   "msg_time INT NOT NULL);"
							   "create index if not exists thread_id_idx on messages (thread_id);"
							   "create index if not exists msg_time_idx on messages (msg_time);"
							   "commit;")
	await cursor.close()
	srv.ctx.session = aiohttp.ClientSession()
	srv.ctx.environment = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'), enable_async=True,
											 autoescape=True)
	srv.ctx.environment.filters['gmtime_ms'] = utc_ms_to_dt


@app.after_server_stop
async def after_stop(srv: sanic.Sanic, loop) -> None:
	await srv.ctx.db.close()
	await srv.ctx.session.close()


async def send_message(db: aiosqlite.Connection, session: aiohttp.ClientSession, message: str,
					   thread_id: str) -> sanic.HTTPResponse:
	if len(message) > 128:
		return sanic.response.text("Message too long", status=400)

	if len(message) == 0:
		return sanic.response.text("Message cannot be empty", status=400)

	msg_time = time.time_ns() // 1_000_000
	async with session.get("https://api.api-ninjas.com/v1/profanityfilter",
						   params={"text": message},
						   headers={"X-Api-Key": os.getenv("PROFANITY_API_KEY")}) as resp:
		if resp.status != 200:
			return sanic.response.text("Failed to create topic, please try again later", status=503)
		message = (await resp.json())['censored']
	cursor = await db.execute("insert into messages values (?,?,?)", (message, thread_id, msg_time))
	await db.commit()
	await cursor.close()
	return sanic.response.empty(status=200)


@app.post("/")
async def new_topic(request: sanic.Request) -> sanic.HTTPResponse:
	if not request.form or 'message' not in request.form:
		return sanic.response.text("Missing message field", status=400)
	return await send_message(request.app.ctx.db, request.app.ctx.session, request.form['message'][0],
							  str(uuid.uuid4()))


@app.post("/thread/<thread_id:str>")
async def reply_topic(request: sanic.Request, thread_id: str) -> sanic.HTTPResponse:
	if not request.form or 'message' not in request.form:
		return sanic.response.text("Missing fields", status=400)

	cursor: aiosqlite.Cursor = await request.app.ctx.db.execute(
		'select exists(select 1 from messages where thread_id=?)',
		(thread_id,))
	thread_exists = (await cursor.fetchone())[0]
	await cursor.close()
	if not thread_exists:
		return sanic.response.text("Invalid ID", status=400)
	return await send_message(request.app.ctx.db, request.app.ctx.session, request.form['message'][0], thread_id)


@app.get("/")
async def index(request: sanic.Request) -> sanic.HTTPResponse:
	id_cursor: aiosqlite.Cursor = await request.app.ctx.db.execute("select distinct thread_id from messages")
	ids = tuple(map(lambda x: x[0], (await id_cursor.fetchall())))
	await id_cursor.close()
	cursor: aiosqlite.Cursor = await request.app.ctx.db.execute(
		"select thread_id,message,min(msg_time) as min_msg_time from messages where thread_id "
		f"in({','.join(('?',) * len(ids))}) group by thread_id order by msg_time DESC",
		ids)

	threads = tuple(map(dict, await cursor.fetchall()))
	await cursor.close()

	template: jinja2.Template = request.app.ctx.environment.get_template('index.html')
	return sanic.response.html(await template.render_async(threads=threads))


@app.get("/thread/<thread_id:str>")
async def get_thread(request: sanic.Request, thread_id: str) -> sanic.HTTPResponse:
	cursor: aiosqlite.Cursor = await request.app.ctx.db.execute(
		"select message,msg_time from messages where thread_id=? order by msg_time DESC", (thread_id,))
	messages = tuple(map(dict, await cursor.fetchall()))
	template = request.app.ctx.environment.get_template('thread.html')
	return sanic.response.html(await template.render_async(messages=messages))


dotenv.load_dotenv()

if __name__ == "__main__":
	app.run(host="0.0.0.0")
