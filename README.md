# adv-database-project

Travelling Social Media App

In order to start the app, run the following commands:

```
python3 -m venv venv
```
```
source venv/bin/activate
```
```
pip install -r requirements.txt
```

Then, create a config.py file with the following content:
```
class Config:
    SQLALCHEMY_DATABASE_URI = 'oracle+cx_oracle://<username>:<password>@localhost:1521/?service_name=XE'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```