from typing import Set, Any

import spacy
import csv
import string
import re
import random
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config
import mysql.connector
from telegram.ext import Updater, CommandHandler, ConversationHandler,MessageHandler,Filters
from telegram import ReplyKeyboardMarkup
import requests
import logging



# responses = ["I'm sorry :( I couldn't find anything like that", '{} is a great hotel!', '{} or {} would work!',
#              '{} is one option, but I know others too :)']
#
#
# def interpret(message):
#     data = interpreter.parse(message)
#     if 'no' in message:
#         data["intent"]["name"] = "deny"
#     return data
#
#
def find_Airbnbs(target,params,filter,excluded):
    if len(target)<1:
        query = 'SELECT * FROM info'
    else:
        query = 'SELECT DISTINCT '
        for tg in target:
            query += tg
            query += ', '
        query = query[:-2]
        query += ' FROM info'
    if len(params) > 0:
        filters = ["{} = '{}'".format(filter,k) for k in params] + ["name!='?'".format(k) for k in excluded]
        query += " WHERE " + " and ".join(filters)
    #t = tuple(params.values())
    query+=" limit 20"
    print(query)
    mydb = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        passwd="Asd123456",
        database="AirbnbNYC"
    )

    mycursor = mydb.cursor()

    try:
        mycursor.execute(query)
        myresult = mycursor.fetchall()
        print(myresult)
        options = set()
        for x in myresult:
            resultNum=len(target)
            if resultNum==0:
                resultNum=len(x)
            result = ''
            for i in range(resultNum):
                result += str(x[i])+" "
            result=result[:-1]


            options.add(result)
    except:
        print("illegal query!")
        return {"Sorry, Database currently in maintain! :("}

    return options


#
# # Create a trainer that uses this config
# trainer = Trainer(config.load("config_spacy.yml"))
#
# # Load the training data
# training_data = load_data('demo-rasa-noents.json')
#
# # Create an interpreter by training the model
# interpreter = trainer.train(training_data)
#

#uncomment to use csv
# def searchdata(conditions):
#     with open('new-york-city-airbnb-open-data/AB_NYC_2019.csv') as csv_file:
#         csv_reader = csv.reader(csv_file, delimiter=',')
#         line_count = 0
#         for condition in conditions:
#             for row in csv_reader:
#                 if line_count == 0:
#                     print(f'Column names are {", ".join(row)}')
#                     line_count += 1
#                 else:
#                     print(f'\t{row[0]} works in the {row[1]} department, and was born in {row[2]}.')
#                     print(row[3])
#                     if line_count>1000:
#                         break
#                     line_count += 1
#             print(f'Processed {line_count} lines.')


rules = {'I want (.*)': ['What would it mean if you got {0} ?',
                         "Why do you want {0} ?",
                         "What's stopping you from getting {0} ?"],
         'do you remember (.*)': ['Did you think I would forget {0} ?',
                                  "Why haven't you been able to forget {0} ?",
                                  'What about {0} ?',
                                  'Yes .. and?'],
         'do you think (.*)': ['if {0}? Absolutely.',
                               'No chance'],
         'if (.*)': ["Do you really think it's likely that {0} ?",
                     'Do you wish that {0} ?',
                     'What do you think about {0} ?',
                     'Really--if {0}']
        }

def match_rule(rules, message):
    for pattern, responses in rules.items():
        match = re.search(pattern, message)
        if match is not None:
            response = random.choice(responses)
            if '{0}' in response:
                var = match.group(1)
                response=response.replace('{0}', var)
            return response
    return "Sorry, I can not understand you. Currently,I can only help you with Airbnb in NYC!"




def replace_pronouns(message):

    message = message.lower()
    if 'me' in message:
        return re.sub('me', 'you', message)
    if 'i' in message:
        return re.sub('i', 'you', message)
    elif 'my' in message:
        return re.sub('my', 'your', message)
    elif 'your' in message:
        return re.sub('your', 'my', message)
    elif 'you' in message:
        return re.sub('you', 'me', message)

    return message


# Define the states
INIT=0
AUTH=1
AUTHED=2
CHOOSE_Airbnb=3
FILTED=4
CHOOSED=5

global_options=tuple()

def send_message(state, pending, message):
    print("USER : {}".format(message))
    p1 = 0
    options=set()
    intent, data=interpret(state,message)
    if data!='None':
        responses={data}
    else:
        responses=set()

    global global_options
    if intent == "1":
        options=find_Airbnbs({"neighbourhood_group"},{},'',[])
        intent='book'
        global_options=(options,"neighbourhood_group")
    elif intent == "2":
        options=find_Airbnbs({"room_type"}, {},'', [])
        intent = 'book'
        global_options = (options, "room_type")
    elif intent == "3":
        options=find_Airbnbs({"price"}, {},'', [])
        intent = 'book'
        global_options = (options, "price")
    elif intent == "4":
        options=find_Airbnbs({"minimum_nights"}, {},'', [])
        intent = 'book'
        global_options = (options, "minimum_nights")

    new_state, response, pending_state = policy_rules[(state, intent)]
    if response == "INIT":
        response = match_rule(rules,message)
    elif response == 'INVALID':
        response="Invalid number, please try again"
    if pending is not None:
        intent, data=interpret(pending[0], message)
        pending = (pending[0], intent)
        new_state, response, pending_state = policy_rules[pending]
        # print("BOT : {}".format(response))
        if pending_state is not None:
            intent, data=interpret(state, message)
            pending = (pending_state, intent)
        else:
            pending = None
        p1=1
    if pending_state is not None:
        intent,data=interpret(state, message)
        pending = (pending_state, intent)
    responses.add(response)
    if p1 == 0:
        # print("BOT : {}".format(response))
        if response == "Wait a moment, I will search for you!":
            choice=''
            for option in options:
                choice+=option+"\n"
            responses.add(choice)
            # print("BOT : {}".format(choice))
    if new_state == AUTHED:
        responses.add("Please Enter:\n 1 for detailed location,\n 2 for detailed Room types,\n "
                      "3 for detailed price range,\n " \
                 "4 for detailed minimum nights")
        # print("BOT : {}".format("Enter 1 for detailed location,\n 2 for detailed Room types,\n 3 for detailed price range,\n 4 for detailed minimum nights"))


    return new_state, pending,responses

def interpret(state,message):
    msg = message.lower()
    if (state == INIT or state == AUTHED) and 'book' in msg or 'airbnb' in msg:
        return 'book','None'
    if state == CHOOSE_Airbnb :
        response=interpretoptions(msg)
        return 'specify_Airbnb',response
    if state == 1 and (any([d in msg for d in string.digits])):
        return 'number','None'
    if state == AUTHED and int(msg)>0 and int(msg)<5:
        return msg,'None'
    if state==FILTED:
        response=interpretsuggestions(msg)
        return 'id', response
    return 'none', 'None'

global_suggestions=set()

def interpretoptions(msg):
    find=0
    global global_options
    global global_suggestions
    for option in global_options[0]:
        if option.lower()in msg:
            msg=option
            find=1
            break
    if find==1:
        suggestions=find_Airbnbs({"id","namel"},{msg},global_options[1],[])
        choice = ''
        for suggestion in suggestions:
            choice += suggestion + "\n"

        global_suggestions=suggestions
        return choice
    else:
        return "Please select one Suggestion listed by me-_-"

def interpretsuggestions(msg):
    find = 0
    global suggestions
    for suggestion in global_suggestions:
        if msg in suggestion:
            find = 1
            break
    if find == 1:
        results = find_Airbnbs({}, {msg}, "id", [])
        choice = ''
        for result in results:
            choice += result + "\n"

        return choice
    else:
        return "Please select one Suggestion listed by me-_-"

# Define the policy rules
policy_rules = {
    (INIT, "none"): (INIT, "INIT", None),
    (INIT, "book"): (AUTH, "you'll have to log in first, what's your phone number?", None),
    (AUTH, "none"): (AUTH, "INVALID", None),
    (AUTH, "number"): (AUTHED, "perfect, welcome back! Which kind of Airbnb do you want?", None),
    (AUTHED, "book"): (CHOOSE_Airbnb, "Wait a moment, I will search for you!", None),
    (AUTHED, "none"): (CHOOSE_Airbnb, "Please select one Option listed by me-_-", None),
    (CHOOSE_Airbnb, "specify_Airbnb"): (FILTED, "perfect, here are my suggestion, you can reply one's id for more details!", None),
    (FILTED, "id"): (CHOOSED, "perfect, I hope my information can help you!", None),
    (CHOOSED, "none"):(INIT,"I am so happy to chat with you! xD", None),
    (CHOOSED, "more"):(AUTHED,"My pleasure!", None)
}


# Define send_messages()
def send_messages(messages,state):
    pending = None
    for msg in messages:
        state, pending,responses = send_message(state,pending, msg)
        return responses, state


def get_url():
    contents = requests.get('https://random.dog/woof.json').json()
    url = contents['url']
    return url

def bop(bot, update):
    url = get_url()
    chat_id = update.message.chat_id
    bot.send_photo(chat_id=chat_id, photo=url)
    return INIT

def location(bot,update):
    chat_id = update.message.chat_id
    bot.send_location(chat_id=chat_id, latitude=45.503958, longitude=-73.574743,
                      live_period=80)
    return INIT


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


reply_keyboard = [['About me', 'My Location'],
                  ['Favourite animal', 'Airbnb'],
                  ['Done']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def start(bot, update):
    update.message.reply_text(
        "Hi! My name is Jarvis. I am an Airbnb assistant in New York city. I am so happy to meet you. "
        "Why don't you tell me something about yourself?",
        reply_markup=markup)

    return INIT


def init_choice(bot, update):
    message=update.message.text
    if message=='About me':
        update.message.reply_text("I am 1 year old! I like blue and chatting.My teacher is Prof. Fan Zhang.", reply_markup=markup)
        state=INIT
    elif 'how are you' in message.lower():
        update.message.reply_text("I am fine, thank you!", reply_markup=markup)
        state = INIT
    elif 'hey' in message.lower() or 'hi' in message.lower():
        update.message.reply_text("Hi!", reply_markup=markup)
        state = INIT
    else:
        responses,state=send_messages([message],INIT)
        print(responses)
        for response in responses:
            update.message.reply_text(response, reply_markup=markup)
        # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state


def auth_choice(bot, update):
    message = update.message.text
    responses,state = send_messages([message], AUTH)
    print(responses)
    for response in responses:
        update.message.reply_text(response, reply_markup=markup)
    # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state

def authed_choice(bot, update):
    message = update.message.text
    responses,state = send_messages([message], AUTHED)
    print(responses)
    for response in responses:
        update.message.reply_text(response, reply_markup=markup)
    # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state

def choose_choice(bot, update):
    message = update.message.text
    responses,state = send_messages([message], CHOOSE_Airbnb)
    print(responses)
    for response in responses:
        update.message.reply_text(response, reply_markup=markup)
    # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state

def filter_choice(bot, update):
    message = update.message.text
    responses,state = send_messages([message], FILTED)
    print(responses)
    for response in responses:
        update.message.reply_text(response, reply_markup=markup)
    # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state

def final_choice(bot, update):
    message = update.message.text
    responses,state = send_messages([message], CHOOSED)
    print(responses)
    for response in responses:
        update.message.reply_text(response, reply_markup=markup)
    # bot.send_message(chat_id=update.effective_chat.id, text=update.message.reply_text(response,reply_markup=markup))
    print(state)
    return state


def done(bot, update):

    update.message.reply_text("I hope to see you soon!")

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater('1010785151:AAEJYwz1vMDVVHbuWlXs1cp7r4n-1UIgJDA')
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            INIT: [MessageHandler(Filters.regex('^(About me|Airbnb)$'),
                                      init_choice),
                   MessageHandler(Filters.regex('^My Location$'),location),

                       MessageHandler(Filters.regex('^Favourite animal$'),
                                      bop),
                            MessageHandler(Filters.regex('^Done$'), done),
                                 MessageHandler(Filters.text,init_choice),

                       ],

            AUTH: [MessageHandler(Filters.text,
                                           auth_choice)
                            ],

            AUTHED: [MessageHandler(Filters.text,
                                  authed_choice)
                   ],

            CHOOSE_Airbnb: [MessageHandler(Filters.text,
                                    choose_choice)
                     ],

            FILTED: [MessageHandler(Filters.text,
                                          filter_choice),
                           ],

            CHOOSED: [MessageHandler(Filters.text,
                                    final_choice),
                     ],

        },

        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

# Send the messages
# send_messages([
#     "I want book airbnb",
#     "I'd like to book some coffee",
#     "555-12345",
#     "2",
#     "shared room",
#     "1177971",
#     "Thank you",
#     "Hi"
# ])

