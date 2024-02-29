import click
import os
import subprocess
import shlex
import sqlite3
from dotenv import load_dotenv
from pyfiglet import Figlet
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter


def list_instance(v_env):
    load_dotenv()
    database_path = os.environ.get("DBPATH")
    conn = sqlite3.connect(f"{database_path}")
    cursor = conn.cursor()
    sqltext = f"select * from tinstance where env_name ='{v_env}';"
    cursor.execute(sqltext)
    result = cursor.fetchall()
    return result


def get_ip_port(v_instance_name):
    load_dotenv()
    database_path = os.environ.get("DBPATH")
    conn = sqlite3.connect(f"{database_path}")
    cursor = conn.cursor()
    sqltext = f"select * from tinstance where instance_name ='{v_instance_name}';"
    cursor.execute(sqltext)
    result = cursor.fetchall()
    return result


def conn_dev(ip_db, port_db, engine_db):
    b_command = ""
    if engine_db == "MySQL":
        b_command = f"mysql -u febridba -p -h {ip_db} -P {port_db}"
    b_command = shlex.split(b_command)
    b_command = subprocess.run(b_command)


def conn_stg(ip_db, port_db, engine_db):
    b_command = ""
    if engine_db == "MySQL":
        b_command = f"mysql -u febridba -p -h {ip_db} -P {port_db}"
    b_command = shlex.split(b_command)
    b_command = subprocess.run(b_command)


def conn_prod(
    ip_db, local_port_db, remote_port_db, engine_db, user_db="", default_db=""
):
    b_command = ""
    base_path = os.path.dirname(os.path.abspath(__file__))
    if engine_db == "MySQL":
        b_command = (
            "sh "
            + base_path
            + f"/bash_script/prod-r-mysql.sh {ip_db} {local_port_db} {remote_port_db}"
        )
    elif engine_db == "RDP":
        b_command = (
            "sh "
            + base_path
            + f"/bash_script/prod-rdp-vm.sh {ip_db} {local_port_db} {remote_port_db}"
        )
    elif engine_db == "Postgres":
        b_command = (
            "sh "
            + base_path
            + f"/bash_script/prod-r-postgresql.sh {ip_db} {local_port_db} {remote_port_db} {user_db} {default_db}"
        )

    b_command = shlex.split(b_command)
    b_command = subprocess.run(b_command)


@click.command()
def interactive_cli():
    custom_fig = Figlet(font="rowancap")
    title = custom_fig.renderText("DB Tools")
    print(title)
    click.echo("Welcome to DBA Tools Interactive CLI!")
    click.echo("Ver 0.1.0")

    # options = ["option1", "option2", "option3", "option4", "option5"]
    options = ["Prod", "STG", "Dev"]
    completer = FuzzyWordCompleter(options)

    user_input = prompt(
        'Choose an option (press "Ctrl+C" to exit): ', completer=completer
    )
    process_user_input(user_input)

    ioptions = []
    for i in list_instance(user_input):
        print(str(i[0]) + " " + str(i[1]) + "-" + str(i[2]))
        ioptions.append(i[1])

    cinstance = FuzzyWordCompleter(ioptions)
    instance_input = prompt("Choose Instance: ", completer=cinstance)
    if instance_input == "":
        exit()

    process_user_input(instance_input)

    ip_port = get_ip_port(instance_input)
    if len(ip_port) == 0:
        click.echo("Instance Not Found")
        exit()
    # COndition Conn Env
    if user_input == "Dev":
        conn_dev(ip_port[0][2], ip_port[0][3], ip_port[0][7])
    elif user_input == "STG":
        conn_stg(ip_port[0][2], ip_port[0][3], ip_port[0][7])
    elif user_input == "Prod":
        conn_prod(
            ip_port[0][2],
            ip_port[0][3],
            ip_port[0][4],
            ip_port[0][7],
            ip_port[0][6],
            ip_port[0][8],
        )

    else:
        exit()


def process_user_input(selected_option):
    click.echo(f"Processing selected option: {selected_option}")


if __name__ == "__main__":
    interactive_cli()
