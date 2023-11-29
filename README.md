# forum

This repository contains code for an anonymous forum.
Users may create and reply to topics, as well as view posts/replies by other users.
An instance is currently hosted [here](http://c4cforum.duckdns.org).

## Components

### Frontend

The frontend consists of three components:
* the home page
* the thread page
* a js script that sends messages

The home page and the thread page are both templates, which allows the server to
populate topics and threads onto the page.

The home page consists of:
* a form consisting of a text box and send button for users to create a new topic, and 
* a list of links to topics, where each link contains the topic
prefixed by the time the topic was created (in UTC) and leads to the corresponding thread 
page.

The thread page consists of:
* a link to the home page,
* a form consisting of a text box and send button for users to reply to messages, and
* a list of messages, prefixed by the time the message was sent
(also in UTC) in descending order of submission time.


The sender script intercepts the form submit event, disables the send button, and posts
the form data to the current url. If the server returns 2xx, the page is reloaded to show
the new topic/message. If not, an alert is shown with an error message from the server
and the send button is re-enabled.

### Backend

#### Database schema
The database is an SQLite database consisting of a single table `messages`
containing 3 columns:
* `message`: a user's message
* `thread_id`: the id of the thread the message was sent in
* `msg_time`: the time at which the message was sent

#### Receiving messages
Messages are sent as form posts to the current page. The form consists of a single field,
`message`, containing the user's message. The form data is validated to check that:
* the message field exists
* the message field is not empty
* the message field is <= 128 chars long

If any of these conditions are violated, 400 is returned along with an error message.

In the case of threads, there is another piece
of information encoded in the url posted to, the thread id. The thread id is a uuid.
The url of a thread is in the format `/thread/<uuid>`. This is extracted from the url
and looked up in the database to see if there is a row with the same thread id.
If no such row exists, 400 is returned along with an error message.

#### Processing messages
Before being added to the database, messages need to be filtered, and also need
a corresponding thread id and message send time. 

##### Filtering
Messages are filtered by passing them
through a profanity filter api. If the api call fails, the server returns 503 and an error
message. If not, the censored message is then recorded.

##### Thread ID
In the case of topics, a uuid is randomly generated for it as it is the 
first message in the thread. In the case of replies, the uuid is already provided.
Topics are just messages with the minimum send time per thread id.

##### Message send time
The time at which the message is sent (in UTC) is recorded in ms.

#### Storing messages
The row, consisting of the filtered message, thread id, and send time, is then inserted
into the database.
The server then returns 200.

#### Displaying messages/topics

##### On the homepage
The database is queried for all messages with the minimum message time in each group with
the same thread id, ordered by the message time in descending order.

This returns all topics.

The results are passed to the templating engine, which displays them as described
previously.

##### On the thread page
The database is queried for all messages with the corresponding thread id (extracted from
the url) ordered by the message time in descending order.

This returns all messages in the thread.

The results are passed to the templating engine, which displays them as described
previously.

#### Misc
##### Time conversion
The time in (UTC) ms is converted to a human-readable date by a custom jinja filter
##### SQLite indices
Indices are created on thread_id and msg_time to speed up queries
##### Static routes
There is a single static route for the sender js script
##### Secrets
The profanity api key is stored in a .env file, loaded into the environment variables
on startup
##### Thread ID considerations
I had considered hashing the topic message with the time that it was posted as a salt
to create a thread id, but figured it was easier to just generate a uuid.

## Requirements
* Users should be able to type a message and post it to the message board.
The message must be non-empty, and at most 128 characters long.
  - Users can type messages into the form on the homepage and send them.
    The messages are validated to ensure that they are between 1-128 chars long. If not,
    an error is shown as an alert.
* Users should be able to see messages on the message board from most to least recent.
  * The messages on the message board are sorted in descending order of submission time
* Users on different computers should be able to post to the same board and view each other’s messages.
  * The messages on the board are persistent and can be viewed by other users on different
    computers. When a user sends a message on a board, users viewing that board will see
    it, though they may need to reload the page to fetch new messages.

## Running
Clone:
```shell
git clone https://github.com/doggo4242/forum.git
cd forum
```
Install requirements:
```shell
python -m pip install -r requirements.txt
```
Run:
```shell
python main.py
```
