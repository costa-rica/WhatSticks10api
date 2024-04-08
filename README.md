
# What Sticks 10 API

![What Sticks Logo](/docs/images/wsLogo_200px.png)

## Description
What Sticks 10 API are a collection of custom Python endpoints that will connect with the What Sticks Database and get Oura Ring data.

Polar and Apple Health coming soon.


## Features
- Users can register
- Users can submit Oura Ring Token and retrieve their sleep data.


## Contributing
We welcome contributions to the WhatSticks10 API project.


For any queries or suggestions, please contact us at nrodrig1@gmail.com.


## Documentation

### ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT
ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT is a variable in ws_config/config.py. If it is set to `True`, it will stop WhatSticks10Api from logging in and registering users. Furthermore, it provides alert_title and alert_message sent by the WS10API that the WSiOS app will display to the user conveying the technical difficulty. The mechanisim this works through is a function in WS10API/utilsDecorators.py.

If it is set to anything except for `True`, it will allow the normal logging in and registering function.


## Project Folder Structure
```
├── README.md
├── app_package
│   ├── __init__.py
│   ├── _common
│   │   ├── __pycache__
│   │   ├── config.py
│   │   ├── token_decorator.py
│   │   └── utilities.py
│   ├── bp_apple_health
│   │   ├── __pycache__
│   │   ├── routes.py
│   │   └── utils.py
│   ├── bp_oura
│   │   ├── __pycache__
│   │   ├── routes.py
│   │   └── utils.py
│   └── bp_users
│       ├── __pycache__
│       ├── routes.py
│       └── utils.py
├── requirements.txt
└── run.py
```
