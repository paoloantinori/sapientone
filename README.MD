##### to build
```
sudo apt-get install -y python-pip python-virtualenv
virtualenv --no-site-packages --distribute .env
source server/.env/bin/activate

pip install -r requirements.txt 
cd server
./run.py
```
