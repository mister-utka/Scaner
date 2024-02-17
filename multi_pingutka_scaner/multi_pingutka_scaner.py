import subprocess
from datetime import datetime
import socket
import argparse
import concurrent.futures
import re
import ipaddress
import struct

from alive_progress import alive_bar


cmd = ["ping", "-c", "3", "-w", "3"]


def get_arguments():
    """Возвращает полученное значение аргументов от пользователя"""
    # Создадим объект, который умеет работать с данными от пользователя
    parser = argparse.ArgumentParser()

    # Сначала мы указываем, что мы ожидаем от пользователя, в dest указываем куда мы занесем данные, а после сообщение
    # Здесь мы обучаем дочерний элемент парсить и создаем опции
    parser.add_argument("-r", "--rangeip", dest="rangeip",
                        help="Specify the range of ip addresses. "
                             "Example 10.10.10.1-10.10.10.255.")
    parser.add_argument("-rf", "--rangeip_file", dest="rangeip_file",
                        help="Specify the file where there will be a range of addresses on each line")
    parser.add_argument("-f", "--file", dest="file",
                        help="Specified after the -r parameter. "
                             "Specify the file in which the found ip addresses will be saved. By default in.")
    parser.add_argument("-s", "--speed", dest="speed",
                        help="It is specified after the -r parameter. "
                             "Specify the speed (number of processes) which will be run in parallel. "
                             "Warning: A large number may cause the computer to freeze or disconnect clients from the access point! "
                             "It is recommended not to exceed 120 for Wi-Fi and 300 for a wired connection.")

    # Он пройдется по введенным значениям пользователем и разобьет их на аргументы и значения
    options = parser.parse_args()

    if not options.rangeip and not options.rangeip_file:
        parser.error("[-] Please specify the ip address range, use --help for more information")
    elif not options.file:
        parser.error("[-] Please specify the file range where the result will be saved, use --help for more information")

    return options


def check_ip(ip):
    '''
    Функция для проверки корректности IP-адреса
    :param ip: ip адрес для проверки
    :return: False/True в зависимости от корректности ip адреса
    '''
    try:
        socket.inet_aton(ip)  # Преобразуем IP-адрес в байтовую строку
        return True  # Возвращаем True, если IP-адрес корректный
    except socket.error:
        return False  # Возвращаем False, если IP-адрес некорректный


def get_available_ips(start_ip, end_ip):
    '''
    Ленивый генератор, который будет возвращать адреса по мере запросов
    :param start_ip: начальный ip адрес из диапазона
    :param end_ip: конечный ip адрес из диапазона
    :return: ip адрес
    '''
    start = struct.unpack('!I', socket.inet_aton(start_ip))[0]
    end = struct.unpack('!I', socket.inet_aton(end_ip))[0]

    for ip in range(start, end + 1):
        ip_address = socket.inet_ntoa(struct.pack('!I', ip))
        yield ip_address


def ping_ip_addr(ip_addr, cmd):
    '''
    Функция запускает icmp пинг
    :param ip_addr: адрес, который будем пинговать
    :param cmd: параметр указываем в начале скрипта
    :return: на выходе получаем вывод команды ping
    '''
    try:
        ip_address_result = subprocess.check_output(cmd + ip_addr.split(" "))
        return ip_address_result
    except subprocess.CalledProcessError:
        pass


def file_ip_sorted(file):
    '''
    Сортируем ip адреса в файле
    :param file: файл для сортировки
    :return: отсортированный файл
    '''
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


def ping_scanning(file, speed, total_ips, ip_addr_list):
    '''
    Функция запускает потоки
    :param file: файл, куда будут сохранены ip адреса
    :param speed: количество потоков
    :param total_ips: кол-во ip адресов в диапазоне
    :param ip_addr_list: ленивый генератор
    :return:
    '''

    print("[+] " + str(total_ips) + " ip addresses will be checked")

    # Так как потоки будут запускаться пачками по 65536 штук, нам нужно узнать сколько циклов на это потребудется
    range_for = total_ips // 65536
    # Переменная для приостановки создания потоков
    flag = 0

    # Создадим прогресс-бар
    with alive_bar(total_ips) as bar:

        # Запуск сканирования
        for i in range(range_for + 1):

            with concurrent.futures.ThreadPoolExecutor(max_workers=speed) as executor:
                futures = []

                for ip_addr in ip_addr_list:

                    future = executor.submit(ping_ip_addr, ip_addr, cmd)
                    futures.append(future)
                    flag += 1
                    # Если мы превысили ограничения по количеству созданных потоков, переходим к обработке ответов
                    if flag >= 65536:
                        break

                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    # Получим из вывода только ip-адреса, которые ответил на пинг и запишем их в файл
                    if result != None:
                        result = str(result)
                        if re.search(r'\s\d%', result):
                            match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result)
                            ip_addr_write = match.group(1)
                            with open(file, 'a') as f:
                                f.write(ip_addr_write + "\n")
                    bar()
            # После того как были обработаны ответы от пачки, запускаем следующею
            flag = 0


def calculating_the_range(range_ip):
    '''
    Получаем диапазон адресов для icmp-сканирования
    и общее количество IP-адресов в диапазоне
    :param range_ip: спарсеная строка разделенная по "-"
    :return: диапазон адресов и общее количество IP-адресов в диапазоне
    '''
    # Получаем диапазон адресов для icmp-сканирования
    start_ip = range_ip[0]
    end_ip = range_ip[1]
    ip_addr_list = get_available_ips(start_ip, end_ip)

    # Преобразуем начальный и конечный IP-адреса в объекты ipaddress.IPv4Address
    start_ip_obj = ipaddress.IPv4Address(start_ip)
    end_ip_obj = ipaddress.IPv4Address(end_ip)
    # Вычисляем общее количество IP-адресов в диапазоне
    total_ips = int(end_ip_obj) - int(start_ip_obj) + 1

    return ip_addr_list, total_ips


def main():

    start_time = datetime.now()

    # Парсим аргументы, переданные пользователем
    options = get_arguments()

    # Указывается файл, куда будут сохранены ip адреса
    file = options.file

    # Указываем скорость (количество потоков)
    speed = options.speed
    if options.speed == None:
        speed = 100
    speed = int(speed)

    # Создаем или очищаем файл, куда будут писаться найденные ip-адреса
    with open(file, 'w'):
        pass

    print("-" * 96)
    print(f'[+] file save: {file}')
    print(f"[+] speed: {speed}")

    # Если был указан один диапазон
    if options.rangeip_file == None:

        # Получаем диапазон адресов для icmp-сканирования
        range_ip = options.rangeip.split('-')
        ip_addr_list, total_ips = calculating_the_range(range_ip)

        # Запуск сканирования
        ping_scanning(file, speed, total_ips, ip_addr_list)

    # Если диапазоны были указанны в файле
    elif options.rangeip_file != None:

        # Получаем файл, откуда будут считываться диапазоны адресов
        with open(options.rangeip_file, 'r') as rangeip_file:

            # Считываем количеств строк в файле
            x = len(rangeip_file.readlines())
            print('[+] Total range:', x)
            # Сброс указателя файла обратно в начало
            rangeip_file.seek(0)
            range_counter = 1

            for line in rangeip_file:

                line = line.replace('\n', '')
                print(f'\n[+] range_counter: {range_counter}/{x}')
                print(f'[+] range: {line}')

                # Получаем диапазон адресов для icmp-сканирования
                range_ip = line.split('-')
                ip_addr_list, total_ips = calculating_the_range(range_ip)

                # Запуск сканирования диапазона
                ping_scanning(file, speed, total_ips, ip_addr_list)
                range_counter += 1

    # Сортируем ip-адреса в файле
    file_ip_sorted(file)

    total_time = datetime.now() - start_time
    print(f'\n[+] Total time: {total_time}')


if __name__ == "__main__":
    main()
