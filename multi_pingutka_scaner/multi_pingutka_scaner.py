import subprocess
import time

import socket
import multiprocessing
import ipaddress
import argparse
import resource


# Определяем максимальный размер памяти в байтах (например, 4GB)
memory_limit = 1000 * 1024 * 1024

# Определяем команду, которая будет выполняться
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

    if not options.rangeip:
        parser.error("[-] Please specify the ip address range, use --help for more information")
    elif not options.file:
        parser.error("[-] Please specify the file range where the result will be saved, use --help for more information")

    return options


def check_ip(ip):
    """Функция для проверки корректности IP-адреса"""
    try:
        socket.inet_aton(ip)  # Преобразуем IP-адрес в байтовую строку
        return True  # Возвращаем True, если IP-адрес корректный
    except socket.error:
        return False  # Возвращаем False, если IP-адрес некорректный


def get_available_ips(start_ip, end_ip):
    """Ленивый генератор для получения доступных IP-адресов"""
    start = list(map(int, start_ip.split('.')))  # Разбиваем начальный IP-адрес на отдельные октеты
    end = list(map(int, end_ip.split('.')))  # Разбиваем конечный IP-адрес на отдельные октеты

    def ip_generator():
        while start <= end:
            ip = '.'.join(map(str, start))  # Собираем IP-адрес из октетов
            if check_ip(ip):  # Проверяем корректность IP-адреса
                yield ip  # Возвращаем доступный IP-адрес
            start[3] += 1  # Увеличиваем последний октет на 1
            for i in (3, 2, 1):
                if start[i] == 256:  # Если октет равен 256, переходим к следующему октету
                    start[i] = 0
                    start[i-1] += 1

    ip_gen = ip_generator()
    return ip_gen


def process_func(ip_gen, total_ips, speed, file):
    """Функция, которая вызывается при создании процесса"""
    progress_bar = 0
    for ip_addr in ip_gen:
        progress_bar += 1 * speed

        try:
            cmd.append(ip_addr)
            output = subprocess.check_output(cmd)
            cmd.pop()

            if (r'\s\d%', output):
                print('\r' + " " * 35, end="")
                print('\r' + " " * 35 + f"\r(!) {ip_addr}" + " " * 35)
                with open(file, 'a') as f:
                    f.write(ip_addr + "\n")
                time.sleep(0.95)

        except subprocess.CalledProcessError:
            if progress_bar > total_ips:
                progress_bar = total_ips
            if len(ip_addr) <= 11:
                print(f"\r(.) {ip_addr}\t\t\t{progress_bar}/{total_ips}", end="")
            else:
                print(f"\r(.) {ip_addr}\t\t{progress_bar}/{total_ips}", end="")
            cmd.pop()

        except KeyboardInterrupt:
            pass


def multiprocessing_ping_functions(start_ip, end_ip, speed, file):
    print("Calculating IP addresses...")
    # Преобразуем начальный и конечный IP-адреса в объекты ipaddress.IPv4Address
    start_ip_obj = ipaddress.IPv4Address(start_ip)
    end_ip_obj = ipaddress.IPv4Address(end_ip)

    # Вычисляем общее количество IP-адресов в диапазоне
    total_ips = int(end_ip_obj) - int(start_ip_obj) + 1

    closest_number = 1
    min_remainder = total_ips % closest_number

    for i in range(2, speed + 1):
        remainder = total_ips % i
        if remainder < min_remainder or min_remainder == 0:
            closest_number = i
            min_remainder = remainder

    speed = closest_number
    print(f"[+] speed: {closest_number}")

    print("[+] " + str(total_ips) + " ip addresses will be checked")
    print("-"*80)
    time.sleep(2)

    # Разбиваем общее количество IP-адресов на число процессов
    chunk_size = total_ips // speed

    # Создаем процессы
    processes = []
    for i in range(speed):
        # Вычисляем начальный и конечный IP-адреса для каждого процесса
        start = start_ip_obj + i * chunk_size
        end = start + chunk_size - 1
        if i == speed - 1:  # Последний процесс может получить немного больше IP-адресов, чтобы учесть остаток
            end = end_ip_obj

        # Создаем генератор IP-адресов для каждого процесса
        ip_gen = get_available_ips(str(start), str(end))

        # Создаем процесс
        process = multiprocessing.Process(target=process_func, args=(ip_gen, total_ips, speed, file))
        processes.append(process)

    try:
        # Запускаем процессы
        for process in processes:
            process.start()

        # Ожидаем завершения процессов
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("\n[+] Detected CTRL + C ..... stopping")
        # Завершаем процессы
        for process in processes:
            process.terminate()


def file_ip_sorted(file):
    """Сортируем ip адреса в файле"""
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


def main():
    # Устанавливаем ограничение на использование памяти
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

    # Начальное время
    start_time = time.time()

    # Парсим аргументы, переданные пользователем
    options = get_arguments()
    # Получаем диапазон адресов для icmp-сканирования
    range_ip = options.rangeip.split('-')
    start_ip = range_ip[0]
    end_ip = range_ip[1]

    # Указывается файл, куда будут сохранены ip адреса
    file = options.file
    print("-" * 80)
    print(f'[+] file save: {file}')

    # Указываем скорость (количество процессов)
    speed = options.speed
    if options.speed == None:
        speed = 100
    speed = int(speed)

    # Создаем или очищаем файл, куда будут писаться найденные ip-адреса
    with open(file, 'w'):
        pass

    multiprocessing_ping_functions(start_ip, end_ip, speed, file)
    file_ip_sorted(file)

    # Конечное время
    end_time = time.time()

    # Разница между конечным и начальным временем
    elapsed_time = round(end_time - start_time, 2)

    if elapsed_time < 60:
        print('\nElapsed time:', elapsed_time, 'second')
    elif 60 <= elapsed_time < 3600:
        minutes = int(elapsed_time / 60)
        seconds = int(elapsed_time - minutes * 60)
        print('\nElapsed time:', minutes, 'minutes', seconds, 'seconds')
    else:
        hours = int(elapsed_time / 3600)
        minutes = int((elapsed_time - hours * 3600) / 60)
        seconds = int(elapsed_time - hours * 3600 - minutes * 60)
        print('\nElapsed time:', hours, 'hours', minutes, 'minutes', seconds, 'seconds')


if __name__ == "__main__":
    main()