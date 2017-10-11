import os
import sys
import json
from threading import Thread, Lock
import logging
from werkzeug.utils import secure_filename
from app import app,socketio
from flask import render_template, request, redirect, url_for, copy_current_request_context
from flask_socketio import send, emit


ALLOWED_EXTENSIONS = set(['txt', 'json'])

current_question = 0
current_game = {}
server = None
thread_lock = Lock()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
@app.route('/index')
def index():
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    return render_template('index.html',
                           title='Home',
                           files= files)



@app.route("/readPin/<pin>")
def readPin(pin):
    try:
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BCM)
    
      GPIO.setup(int(pin), GPIO.IN)
      if GPIO.input(int(pin)) == True:
         response = "Pin number " + pin + " is high!"
      else:
         response = "Pin number " + pin + " is low!"
    except:
      response = "There was an error reading pin " + pin + "."

    templateData = {
      'title' : 'Status of Pin' + pin,
      'response' : response
      }

    return render_template('pin.html', **templateData)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect("/")
    return render_template('upload.html')


@app.route("/start/<game>")
def startGame(game):
    try:
      with open(os.path.join(app.config['UPLOAD_FOLDER'] , game)) as data_file:
        global current_game
        logger.info ("A new game has been requested: " + game)
        current_game = json.load(data_file)
      
    except IOError as err:
        logger.err(err)
    return render_template('play.html', name=current_game["name"], question=current_game["questions"][0]['question'])

@app.route("/question/<next>")
def nextQuestion(next):
    global current_game, current_question
    return render_template('play.html', name="doesn't matter", question=current_game["questions"][int(next)]['question'])


@app.route("/respond/<game>")
def respond(game):
    data = ""
    try:
      with open(os.path.join(app.config['UPLOAD_FOLDER'] , game)) as data_file:    
        data = json.load(data_file)
    except IOError as err:
        logger.err(err)
    return render_template('play.html', data=data, game=game)

@socketio.on('my event', namespace='/test')
def handle_my_custom_event(json):
    logger.info('========== received json: ' + str(json))
    with thread_lock:
      socketio.start_background_task(target=solver)


def solver():
  global current_question, current_game
  current_question = 0
  try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
  except:
    response = "There was an error setting up GPIO."
    logging.error(response)
  
  logger.info("""Current game is: "{0}" """.format(current_game))
  current_qa = current_game['questions'][current_question]
  logger.info("""Current question is: "{0}" """.format(current_qa['question']))
  logger.info("""Current right answer is: "{0}" """.format(current_qa['answer']))

  logger.info("timer started")
  socketio.sleep(5)
  logger.info("timer expired")

  questions_n = len(current_game['questions'])
  for n in range(0, questions_n):
    pin = current_qa['answer'][n]
    GPIO.setup(int(pin), GPIO.IN)
    
    while True: 
      if GPIO.input(int(pin)) == True:
        logger.info("Detected the correct pin.")
        current_question = current_question + 1
        socketio.emit('next question', current_question, namespace='/test')
        break
      else:
        logger.info("Detected the wrong pin.")
        current_question = 0
        socketio.emit('lost', current_question, namespace='/test')
    

  socketio.emit('win', current_question, namespace='/test')
  return