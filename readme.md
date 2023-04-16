# Disk Drive Bot

This repository was created to demonstrate the capabilities of the 
[Telegram Django Bot Bridge library](https://github.com/alexanderaleskin/telegram_django_bot_bridge). This example shows,
that with using Telegram Django Bot Bridge it is possible:

* To reduce code from 2-3 thousand of lines to one thousand;
* To create a logical structure of bot code
* To use same code patterns in same situations.

This example bot implements a file storage system in Telegram like Google Drive or Yandex Disk. It has:

* File and folder managing;
* Sharing files and folders with different types of access;
* Localization.


The code is provided under the CC0 License without any restrictions and obligations for use. 
[@Disk_Drive_Bot](https://t.me/Disk_Drive_Bot) is a running instance for demonstrating logic of the code.
You can test and see how it works, and you can also use it for its intended purpose 😀

This repository provides an example of the implementation of storing documents in the cloud storage, where the storage
is Telegram. The bot gives the ability for creating files, folders, and sharing data with others.

The project has the following folders and items:

1. base - the main directory with all business logic of the bot;
2. bot_conf - settings for launching Django and Telegram Django Bot bridge;
3. configs - files for running docker containers;
4. locale - translation for supporting localization (in this case Russian only, English used by definition);
5. run_bot.py - this is the file that starts the bot;
6. common.yml, docker-compose.yml, docker-entrypoint.sh, Dockerfile - files for running docker.

The easiest way to run your own bot is via docker-compose:

1. create and fill the .env file as specified in the .env.example;
2. start the containers by running the following command from the project directory: ```docker-compose up```.

Make sure docker and docker-compose are installed on your machine.


## Template for your projects

This repository was created for demonstration purposes and is not intended to be reused in 
creating other projects. For initialization use the [Telegram Django Bot Template](https://github.com/alexanderaleskin/telergam_django_bot_template) repository.
There is also more detailed information on directory architecture and files.

To study certain implementation features, go to the 
[Telegram Django Bot Bridge library](https://github.com/alexanderaleskin/telegram_django_bot_bridge).

