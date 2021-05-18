import os
from dotenv import load_dotenv
from fabric import Connection
from invoke import Responder


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "dev.env"))


def install_package(c):
    c.sudo('apt-get update')
    c.sudo('apt-get install libpq-dev postgresql postgresql-contrib -y')
    c.sudo('apt-get install nginx -y')
    c.sudo('apt-get install supervisor -y')
    c.sudo('apt-get install python3-pip -y')
    c.sudo('pip3 install virtualenv')


def create_database(c):
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    c.sudo('psql -c "CREATE USER %s WITH NOCREATEDB NOCREATEUSER " \
         "ENCRYPTED PASSWORD E\'%s\'"' % (db_user, db_pass), user='postgres')
    c.sudo('psql -c "CREATE DATABASE %s WITH OWNER %s"' % (
         db_name, db_user), user='postgres')


def git_pull(c):
    watchers = [
        Responder(pattern=r"Password for .*", response=f"{os.getenv('GIT_PASSWORD')}\n")
    ]

    with c.cd(os.getenv('DIR_PROJECT')):
        result = c.run("git pull", pty=True, watchers=watchers)


def install_python_package():
    commands = [
        create_venv(),
        set_venv() + ' && ' + 'pip install -r requirements.txt',
    ]
    return commands


def install_in_project_dir(c, commands=None):
    with c.cd(os.getenv('DIR_PROJECT')):
        for command in commands:
            c.run(command)


def set_venv():
    command = "source env/bin/activate"
    return command


def create_venv():
    command = "virtualenv env"
    return command


def set_nginx_config(c):
    with open(os.path.join(os.getenv('CONF_DIR'), 'nginx.conf'), 'r') as reader:
        nginx_conf = reader.read()
        with c.cd('/etc/nginx/sites-enabled/'):
            c.run('echo {} > server.conf'.format(nginx_conf))


def set_gunicorn_config_to_supervisor(c):
    with open(os.path.join(os.getenv('CONF_DIR'), 'gunicorn.conf'), 'r') as reader:
        gunicorn_conf = reader.read()
        with c.cd('/etc/supervisor/conf.d/'):
            c.run('echo {} > gunicorn.conf'.format(gunicorn_conf))
    c.sudo('supervisorctl update')


def restart_server(c):
    c.sudo('supervisorctl restart all')
    c.sudo('service nginx restart')


if __name__ == '__main__':
    conn = Connection(host=os.getenv('SERVER_HOST'), connect_kwargs={'password': os.getenv('SERVER_PASSWORD')})
    install_package(conn)
    create_database(conn)
    git_pull(conn)
    install_in_project_dir(conn)
    set_nginx_config(conn)
    set_gunicorn_config_to_supervisor(conn)
    restart_server(conn)
