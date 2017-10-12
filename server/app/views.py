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
thread_lock = Lock()
timeout = -1
game_in_progress = False

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
    progress = (1.0  / len(current_game["questions"]) ) * 100
    progress = ('%.2f' % progress).rstrip('0').rstrip('.')
    return render_template('play.html', 
                            name=current_game["name"],
                            question=current_game["questions"][0]['question'],
                            progress=progress)

@app.route("/question/<next>")
def nextQuestion(next):
    global current_game, current_question
    progress = (1.0  / len(current_game["questions"]) ) * 100
    progress = ('%.2f' % progress).rstrip('0').rstrip('.')
    return render_template('play.html', 
                           question=current_game["questions"][int(next)]['question'],
                           progress=progress)


@app.route('/manage')
def manage():
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    return render_template('manage.html',
                           files= files)

@app.route('/delete/<game>')
def delete(game):
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'] , game))
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    return render_template('manage.html',
                           files= files)


@app.route('/win')
def win():
    global game_in_progress
    game_in_progress = False
    return render_template('win.html')

@app.route('/lost')
def lost():
    global game_in_progress
    game_in_progress = False
    return render_template('lost.html')

@app.route('/timeout')
def timedout():
    global timeout, game_in_progress
    game_in_progress = False
    timeout = -1
    return render_template('timeout.html')

@socketio.on('connected', namespace='/test')
def handle_my_custom_event(json):
    global game_in_progress
    logger.info('========== received json: ' + str(json))
    if not game_in_progress:
        with thread_lock:
            game_in_progress = True
            socketio.start_background_task(target=solver)


def solver():
  logger.info("__invoking solver")
  global current_question, current_game, timeout
  current_question = 0

  if "timer" in current_game:
    timeout = int(current_game["timer"]["timeout"])
    socketio.start_background_task(target=timer)

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

#   logger.info("timer started")
#   socketio.sleep(5)
#   logger.info("timer expired")
#   socketio.emit('next question', current_question +1, namespace='/test')
#   return

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

def timer():
    global timeout
    while True:
      if(timeout == 0):
          socketio.emit('timeout',  namespace='/test')
      socketio.emit('tick', timeout    , namespace='/test')
      socketio.sleep(1)
      timeout = timeout - 1

      