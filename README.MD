##### to build
```
sudo apt-get install -y python-pip python-virtualenv git python-rpi.gpio
git clone  https://github.com/paoloantinori/sapientone
cd sapientone/

virtualenv --no-site-packages --distribute .env
source .env/bin/activate

pip install -r requirements.txt 
cd server
./run.py
```
