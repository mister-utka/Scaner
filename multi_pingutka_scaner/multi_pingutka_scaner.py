#/usr/bin/python3
import subprocess
import re
import socket
import multiprocessing
import numpy as np
import argparse
import time
import resource

# Определяем максимальный размер памяти в байтах (например, 4GB)
memory_limit = 4000 * 1024 * 1024

# Определяем команду, которая будет выполняться
cmd = ["ping", "-c", "2", "-w", "2"]


def get_arguments():
    """Возвращает полученное значение аргументов от пользователя"""
    # Создадим объект, который умеет работать с данными от пользователя
    parser = argparse.ArgumentParser()

    # Сначала мы указываем, что мы ожидаем от пользователя, в dest указываем куда мы занесем данные, а после сообщение
    # Здесь мы обучаем дочерний элемент парсить и создаем опции
    parser.add_argument("-r", "--rangeip", dest="rangeip", help="Specify the range of ip addresses. "
                                                                              "Example 10.10.10.1-10.10.10.255.")
    parser.add_argument("-f", "--file", dest="file", help="Specified after the -r parameter. "
                                                                        "Specify the file in which the found ip addresses will be saved. By default in.")
    parser.add_argument("-s", "--speed", dest="speed", help="It is specified after the -r parameter. "
                                                                          "Specify the speed (number of processes) which will be run in parallel. "
                                                                          "Warning: A large number may cause the computer to freeze or disconnect clients from the access point! "
                                                                          "It is recommended not to exceed 120 for Wi-Fi and 300 for a wired connection.")

    # Он пройдется по введенным значениям пользователем и разобьет их на аргументы и значения
    options = parser.parse_args()

    if not options.rangeip:
        parser.error("[-] Please specify the ip address range, use --help for more information")
    elif not options.file:
        parser.error("[-] Please specify the file range where the result will be saved, use --help for more information")

    return options

# ################## Функции для получения ip адресов, существующих в сети ########################################### #

def check_ip(ip):
    """Функция для проверки корректности IP-адреса"""
    try:
        socket.inet_aton(ip)  # Преобразуем IP-адрес в байтовую строку
        return True  # Возвращаем True, если IP-адрес корректный
    except socket.error:
        return False  # Возвращаем False, если IP-адрес некорректный

def get_available_ips(start_ip, end_ip):
    """Функция для составления списка возможных IP-адресов"""
    print("Calculating IP addresses...")
    start = list(map(int, start_ip.split('.')))  # Разбиваем начальный IP-адрес на отдельные октеты
    end = list(map(int, end_ip.split('.')))  # Разбиваем конечный IP-адрес на отдельные октеты
    result = []  # Список для хранения доступных IP-адресов
    numbers = 0

    while start <= end:
        ip = '.'.join(map(str, start))  # Собираем IP-адрес из октетов
        if check_ip(ip):  # Проверяем корректность IP-адреса
            result.append(ip)  # Добавляем доступный IP-адрес в список
            numbers += 1
        start[3] += 1  # Увеличиваем последний октет на 1
        for i in (3, 2, 1):
            if start[i] == 256:  # Если октет равен 256, переходим к следующему октету
                start[i] = 0
                start[i-1] += 1

    print("\r[+] " + str(numbers) + " ip addresses will be checked")
    print("-" * 80)
    return result, numbers  # Возвращаем список доступных IP-адресов

def existing_ip_address(available_ips, num_parts):
    """Функция ищет ip-адреса, которые существуют в сети
       Ее используют созданные процессы функции multiprocessing_ping_functions"""
    global progress_bar
    # Создадим пустой список, куда будет записываться вывод команды ping
    existing_ip_address_list = []
    # Создадим пустой список, куда будем помещать существующие ip адреса
    existing_ip_address_list_itog = []
    # Проходимся по доступным ip-адресам, которые мы получили из функции get_available_ips
    for ip_address in available_ips:
        progress_bar += 1 * num_parts
        try:
            cmd.append(ip_address)
            ip_address_result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            cmd.pop()
            if (r'\s\d%', ip_address_result):
                print('\r'+" "*60, end="")
                print('\r'+" "*60 + f"\r(!) {ip_address}"+" "*100)
            # Добавляем вывод команды ping в список
            existing_ip_address_list.append(ip_address_result)
        except subprocess.CalledProcessError:

            if progress_bar > number_of_addresses_to_scan:
                progress_bar = number_of_addresses_to_scan
            print(f"\r(.) {ip_address}  \t\t{progress_bar}/{number_of_addresses_to_scan}", end="")
            cmd.pop()

        # Получаем из списка вывода команды ping только ip адреса, которые ответили на пинг
        for i in existing_ip_address_list:
            i = str(i)
            ip_address = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', i).group()
            existing_ip_address_list_itog.append(ip_address)
    # Удаляем одинаковые ip адреса
    existing_ip_address_list_itog = set(existing_ip_address_list_itog)

    return existing_ip_address_list_itog

def multiprocessing_ping_functions(available_ips, rangeip, file, speed):
    """Функция выполняет сканирование сети с помощью параллельного выполнения icmp запросов,
       что позволяет нам значительно увеличить скорость"""

    global progress_bar
    progress_bar = 0

    def func(available_ips, file, speed):
        """Функция, которая вызывается при создании процессов"""
        existing_ip = existing_ip_address(available_ips,speed)
        with open(file, "a") as file_ip_session:
            for line in existing_ip:
                file_ip_session.write(line + "\n")

    def split_list(lst, speed):
        """Функция разделяет список ip адресов на заданное количество частей (speed)."""
        np_lst = np.array(lst)
        split_lists = np.array_split(np_lst, speed)
        return split_lists

    def number_of_multiprocessors(available_ips, speed):
        """Функция, которая создает процессы в кол-ве, зависимом от переданном speed"""

        # Создадим переменные, которым будем назначать части диапазонов ip адресов
        values = []
        for v in range(1, speed + 1):
            values.append("var" + str(v))

        # Разделяем полученные ip адреса на количество speed
        split_lists = split_list(available_ips, speed)

        # Создаем кортеж списков с разделенными диапазонами ip адресов
        for i, sublist in enumerate(split_lists):
            # print(sublist)
            values[i] = []
            values[i] = [sublist]

        # Получаем из этого кортежа списки, для того чтобы одновременно передать их процессам
        lst = {}
        for i in range(speed):
            arr = np.array(values[i])
            lst[f"lst{i + 1}"] = arr[0].tolist()

        try:
            # создание процессов
            processes = []
            for i in range(1, speed + 1):
                process = multiprocessing.Process(target=func, args=(lst[f"lst{i}"], file, speed))
                processes.append(process)

            # Запуск процессов
            for process in processes:
                process.start()

            # Ожидание завершения процессов
            for process in processes:
                process.join()

        except KeyboardInterrupt:
            pass

    # Очищаем файл, куда пишутся ip-адреса, перед новой сессией
    with open(file, "w"):
        pass
    # Запускаем процессы
    number_of_multiprocessors(available_ips, speed)
    # Сортируем ip адреса в файле
    with open(file, 'r+') as file:
        # Читаем IP-адреса из файла
        ip_addresses = file.readlines()
        # Удаляем символ новой строки из каждого IP-адреса
        ip_addresses = [ip.strip() for ip in ip_addresses]
        # Сортируем IP-адреса
        sorted_ip_addresses = sorted(ip_addresses, key=lambda ip: socket.inet_aton(ip))
        # Перемещаем указатель файла в начало
        file.seek(0)
        # Перезаписываем отсортированные IP-адреса в файл
        for ip in sorted_ip_addresses:
            file.write(ip + '\n')
        # Обрезаем файл после последнего записанного IP-адреса
        file.truncate()

    print('\n'+("-" * 80))
    print("[+] " + "icmp scan completed")

def main():
    # Начальное время
    start_time = time.time()

    # Устанавливаем ограничение на использование памяти
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

    # Парсим аргументы, переданные пользователем
    options = get_arguments()
    # Получаем диапазон адресов для icmp-сканирования
    range_ip = options.rangeip
    # Указывается файл, куда будут сохранены ip адреса
    file = options.file
    print(f'[+] file save: {file}')
    # Указываем скорость (количество процессов)
    speed = options.speed
    if not options.speed == None:
        print(f'[+] speed: {speed}')
    else:
        speed = 100
        print(f'[+] speed: {speed}')
    speed = int(speed)

    # Если есть аргумент -r, то выполняется сканирование на доступные ip адреса
    if not range_ip == None:
        # Задаем начальный и конечный диапазон ip-адресов
        start_ip, end_ip = options.rangeip.split("-")

        # Получаем все ip-адреса из данного диапазона
        global number_of_addresses_to_scan
        available_ips, number_of_addresses_to_scan = get_available_ips(start_ip, end_ip)
        try:
            # Выполнение мультипроцессорного icmp-сканирования сети
            multiprocessing_ping_functions(available_ips, range_ip, file, speed)
        except KeyboardInterrupt:
            print("\n[+] Detected CTRL + C ..... stopping")

    # Конечное время
    end_time = time.time()

    # Разница между конечным и начальным временем
    elapsed_time = round(end_time - start_time, 2)

    if elapsed_time < 60:
        print('Elapsed time: ', elapsed_time, ' second')
    elif 60 < elapsed_time < 3600:
        minutes = str(round(elapsed_time/60, 0)).replace(".0", "")
        second = str(round(elapsed_time - int(minutes)*60, 0)).replace(".0", "")
        if int(minutes) > 60:
            hours = str(round(int(minutes)/60, 0)).replace(".0", "")
            minutes = str(round(int(minutes) - int(hours) * 60, 0)).replace(".0", "")
            print('Elapsed time:', hours, "hours", minutes, ' minutes', second, 'second')
        print('Elapsed time:', minutes, 'minutes', second, 'second')

if __name__ == "__main__":
    main()
