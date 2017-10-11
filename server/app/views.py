import os
import sys
import json
from threading import Thread
import logging
from werkzeug.utils import secure_filename
from app import app
from flask import render_template, request, redirect, url_for


ALLOWED_EXTENSIONS = set(['txt', 'json'])

current_question = 0
current_game = {}
server = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def solver(game):
    try:
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BCM)
    except:
      response = "There was an error reading pin " + pin + "."
      logging.error(response)
      return

    logger.info ("Solver has started for game: " + game)
    logger.info("""Current game is: "{0}" """.format(current_game))
    current_qa = current_game['questions'][current_question]
    logger.info("""Current question is: "{0}" """.format(current_qa['question']))
    logger.info("""Current right answer is: "{0}" """.format(current_qa['answer']))

    questions_n = len(current_game['questions'])
    for n in range(0, questions_n):
      pin = current_qa['answer'][n]
      GPIO.setup(int(pin), GPIO.IN)
      
      while True: 
        if GPIO.input(int(pin)) == True:
          logger.info("Detected the correct pin.")
          break
        else:
           logger.info("Detected the wrong pin.")
    return


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
      server = Thread(target=solver, args=(game,))
      server.setDaemon(True)
      server.start()
    except IOError as err:
        print err
    return render_template('play.html', name=current_game["name"], question=current_game["questions"][0]['question'])

@app.route("/play/<game>/<question>")
def playGame(game, question):
    data = ""
    try:
      with open(os.path.join(app.config['UPLOAD_FOLDER'] , game)) as data_file:    
        data = json.load(data_file)
    except IOError as err:
        print err
    return render_template('play.html', name=data["name"], question=data["questions"][int(question)]['question'])


@app.route("/respond/<game>")
def respond(game):
    data = ""
    try:
      with open(os.path.join(app.config['UPLOAD_FOLDER'] , game)) as data_file:    
        data = json.load(data_file)
    except IOError as err:
        print err
    return render_template('play.html', data=data, game=game)
