from subprocess import check_output
import re
import socket
import multiprocessing
import numpy as np
import argparse
import resource

# Определяем максимальный размер памяти в байтах (например, 2GB)
memory_limit = 2000 * 1024 * 1024

# Определяем команду, которая будет выполняться
cmd = ["nmap", "-sS", "-sV", "-O"]
#cmd = ["nmap", "-sS", "-p", "80,443,8080,1080", "--open"]
#cmd = ["proxychains4", "nmap", "-sT", "-PN", "-sV", "-O", "-r"]


def get_arguments():
    """Возвращает полученное значение аргументов от пользователя"""
    # Создадим объект, который умеет работать с данными от пользователя
    parser = argparse.ArgumentParser()

    # Сначала мы указываем, что мы ожидаем от пользователя, в dest указываем куда мы занесем данные, а после сообщение
    # Здесь мы обучаем дочерний элемент парсить и создаем опции

    parser.add_argument("-r", "--range", dest="range",
                        help="Specify the file from where the ip addresses will be read.")
    parser.add_argument("-f", "--file", dest="file",
                        help="Specify the keyword for the session. The output of this session "
                             "will be saved to files starting with the keyword.")
    parser.add_argument("-s", "--speed", dest="speed",
                        help="It is specified after the -r parameter. "
                             "Specify the speed (number of processes) which will be run in parallel. "
                             "Warning: A large number may cause the computer to freeze.")
    parser.add_argument("-c", "--clear_ip", dest="clear_ip", action="store_true",
                        help="It is specified after the -r parameter. "
                        "Get only ip addresses at the output")

    # Он пройдется по введенным значениям пользователем и разобьет их на аргументы и значения
    options = parser.parse_args()

    if not options.range:
        parser.error("[-] Please specify the file from where the ip addresses will be read, use --help for more information.")
    elif not options.file:
        parser.error("[-] Please specify the keyword for the session, use --help for more information.")

    return options


def check_ip(ip):
    """Функция для проверки корректности IP-адреса"""
    try:
        socket.inet_aton(ip)  # Преобразуем IP-адрес в байтовую строку
        return True  # Возвращаем True, если IP-адрес корректный
    except socket.error:
        return False  # Возвращаем False, если IP-адрес некорректный


def multiprocessing_nmap_functions(list_ip_address_target, file_save, speed, clear_ip):
    """Функция выполняет сканирование сети с помощью параллельного выполнения icmp запросов,
       что позволяет нам значительно увеличить скорость"""
    global progres_bar
    progres_bar = 0

    def nmap_scan(list_ip_address_target):
        """Функция, которая вызывается при создании процессов"""
        for ip_address_target in list_ip_address_target:

            check = check_ip(ip_address_target)
            if check == False:
                print(f"")

            global progres_bar
            progres_bar += 1*speed

            cmd.append(ip_address_target)
            nmap = check_output(cmd)
            cmd.pop()
            nmap_string = nmap.decode('utf-8')
            information_output = ip_address_target + "\n"
            try:
                # Получаем OS
                os = re.search(r"OS details: (.*)", nmap_string)
                information_output = information_output + os[1] + "\n"
            except TypeError:
                pass
            try:
                # Получаем открытые порты
                ports = re.findall(r"\d+/tcp.*", nmap_string)
                for line in ports:
                    information_output = information_output + line + "\n"
            except TypeError:
                pass

            #print(f'info: {information_output}')
            # Если задан параметр -c, то получаем только ip адреса, у которых был не 0 вывод
            if clear_ip:
                if len(information_output) < 16:
                    pass
                else:
                    with (open(f"{file_save}_nmap_session", "a") as file_nmap_session):
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', information_output)
                        ip_address = match.group(1) + "\n"
                        print('\r' + " " * 30, end="")
                        print(f'\r(!) {ip_address}', end="")
                        file_nmap_session.write(ip_address)
            else:
                if len(information_output) < 16:
                    pass
                else:
                    with open(f"{file_save}_nmap_session", "a") as file_nmap_session:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', information_output)
                        ip_address = match.group(1) + "\n"
                        print('\r' + " " * 30, end="")
                        print(f'\r(!) {ip_address}', end="")
                        file_nmap_session.write(information_output + ("-" * 117) + "\n")
            print(f"\r(.) progress: {progres_bar}", end="")

    def split_list(lst, speed):
        """Функция разделяет список ip адресов на заданное количество частей (speed)."""
        np_lst = np.array(lst)
        split_lists = np.array_split(np_lst, speed)
        return split_lists

    def number_of_multiprocessors(list_ip_address_target, speed):
        """Функция, которая создает процессы в кол-ве, зависимом от переданном num_parts"""

        # Создадим переменные, которым будем назначать части диапазонов ip адресов
        values = []
        for v in range(1, speed + 1):
            values.append("var" + str(v))

        # Разделяем полученные ip адреса на количество num_parts
        split_lists = split_list(list_ip_address_target, speed)

        # Создаем кортеж списков с разделенными диапазонами ip адресов
        for i, sublist in enumerate(split_lists):
            values[i] = []
            values[i] = [sublist]

        # Получаем из этого кортежа списки, для того чтобы одновременно передать их процессам
        lst = {}
        for i in range(speed):
            arr = np.array(values[i])
            lst[f"lst{i + 1}"] = arr[0].tolist()

        # создание процессов
        processes = []
        for i in range(1, speed + 1):
            process = multiprocessing.Process(target=nmap_scan, args=(lst[f"lst{i}"],))
            processes.append(process)

        # Запуск процессов
        for process in processes:
            process.start()

        # Ожидание завершения процессов
        for process in processes:
            process.join()

    # Очищаем файл, куда пишутся nmap вывод, перед новой сессией
    with open(f"{file_save}_nmap_session", "w"):
        pass
    print("-" * 80)
    print("[+] " + f"Start nmap-scanning. {speed} processes are running")
    print("-" * 80)
    # Запускаем процессы
    number_of_multiprocessors(list_ip_address_target, speed)
    print("\n" + "-" * 80)
    print("[+] " + f"End nmap-scanning.")


def sorting_nmap_out(file_save, clear_ip):
    """Функция производит сортировку вывода, полученного от процессов nmap"""

    def nmap_session_sorted(file_save):
        """Так как процессы заканчиваются неравномерно, нужно отсортировать данные, записанные
        в nmap_session, после чего отсортированный вариант будет в nmap_session_sorted"""

        # Очищаем файл, куда пишутся nmap вывод, перед новой сессией
        with open(f"{file_save}_nmap_session_sorted", "w"):
            pass

        # Чтение содержимого файла nmap_session для сортировки
        with open(f'{file_save}_nmap_session', 'r') as file:
            content = file.read()

        if clear_ip:
            blocks = re.split('\n', content)
        else:
            # Разделение содержимого на блоки записей
            blocks = re.split('-{100}', content)

        # Извлечение IP-адреса и связанных данных для каждого блока записей
        records = []
        for block in blocks:
            match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', block)
            if match:
                ip_address = match.group(1)
                data = block.replace(ip_address, '').strip()
                records.append((ip_address, data))

        # Сортировка блоков записей по IP-адресам
        sorted_records = sorted(records, key=lambda x: [int(num) for num in x[0].split('.')])

        # Запись отсортированных блоков записей в новый файл
        with open(f'{file_save}_nmap_session_sorted', 'w') as file:
            for record in sorted_records:
                file.write((record[0] + '\n').replace("-", ""))
                file.write((record[1] + '\n').replace("-", ""))
                if clear_ip:
                    pass
                else:
                    file.write('-' * 100 + '\n')
        # Удаление всех пустых строк из файла
        with open(f'{file_save}_nmap_session_sorted', 'r+') as file:
            lines = file.readlines()
            file.seek(0)
            file.truncate()
            for line in lines:
                if line.strip():
                    file.write(line)

    def nmap_session_sorted_windows(file_save):
        """Так же отсортируем отдельно машины Windows и запишем их в файл windows_devices"""

        # Получаем с помощью re выражения все машины Windows
        with open(f'{file_save}_nmap_session_sorted', 'r') as file:
            # Считываем все строки файла в одну строку
            content = file.read()
            # Получаем все машины Windows с их данными
            line = re.findall("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\nMicrosoft Windows(.*\n)*?)-", content)
            result = '\n'.join([''.join(match) for match in line])
            # Заменяем пустые строки на ---
            result = (str(result)).replace("\n\n", "\n"+"-"*117+"\n")

        # Записываем полученные данные в файл
        with open(f'{file_save}_windows_devices', 'w') as file:
            file.write(result)

    nmap_session_sorted(file_save)
    nmap_session_sorted_windows(file_save)


def main():
    # Устанавливаем ограничение на использование памяти
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

    # Парсим аргументы, переданные пользователем
    options = get_arguments()

    # Указывается файл, откуда будут считываться ip-адреса
    range_file = options.range
    # Указывается ключевое слово для сессии
    file_save = options.file
    print(f"[+] file session save:\t\t {file_save}_nmap_session\n"
          f"    file session sorted save:\t {file_save}_nmap_session_sorted")
    # Указываем скорость (количество процессов)
    speed = options.speed
    # Указываем, нужно ли получить только ip-адреса
    clear_ip = options.clear_ip
    if not options.speed == None:
        print(f'[+] speed: {speed}')
    else:
        speed = 50
        print(f'[+] speed: {speed}')
    speed = int(speed)
    try:
        # Получим список ip-адресов, которые будут сканироваться nmap-ом
        with open(range_file, "r") as f:
            list_ip_address_target = []
            for ip_address_target in f:
                # print(ip_address_target.rstrip())
                list_ip_address_target.append(ip_address_target.rstrip())
    except FileNotFoundError:
        print(f"[-] The file {range_file} does not exist. Check if the path is specified correctly")
        quit()
    # Запуск мультипроцессорного nmap сканирования
    multiprocessing_nmap_functions(list_ip_address_target, file_save, speed, clear_ip)
    # Отсортируем данные, записанные процессами
    sorting_nmap_out(file_save, clear_ip)


if __name__ == "__main__":
    main()
