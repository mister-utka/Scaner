Данный код позволит провести сканирование сети с помощью параллельных nmap сканирований.

Регулировать параметры команды можно в строчке:

cmd = ["nmap", "-sS", "-sV", "-O"]

Скорость зависит от типа Вашего подключения и мощности железа. Идея заключается в большом количестве параллельных nmap
сканирований. 

Предупреждения!

В коде предусмотренно ограничение на выделение памяти ОЗУ, так как без него программа может поглотить ее всю, что приведет
к зависанию компьютера. Вы можете регулировать это в строчке 

memory_limit = 2000 * 1024 * 1024

где число 2000 - это выделение памяти в МБ.

Так же при подключении по беспроводной сети и выставлении очень большой скорости у клиентов может пропасть подключение,
что может выдать Вас. Рекомендуется запустить ping в соседнем терминале до какого нибудь доменного ресурса, и, если при
работе программы эти ping-и начинают теряться, значит точка не справляется с потоком большого количества маленьких пакетов. 

Пример использования:

python3 multi_nmaputka_scaner.py -r read_ip_file -f save_file -s 100 

где:

-r - файл, с которого будут считываться ip-адреса

-f - ключевое слово для сессии, с которого будут начинаться файлы, куда будет сохранен результат 

-s - количество параллельных процессов, которые будут запущены (по умолчанию 50)

-c - получить на выходе только ip-адреса, без вывода результата nmap (не обязательный параметр)

########################################################################################################################

This code will allow you to scan the network using parallel nmap scans.

You can adjust the parameters of the command in the line:

cmd = ["nmap", "-sS", "-sV", "-O"]

The speed depends on the type of your connection and the power of the hardware. The idea is to have a large number of parallel nmap
scans.

Warnings!

The code provides a limit on the allocation of RAM memory, since without it the program can absorb it all, which will cause
the computer to freeze. You can adjust this in the line

memory_limit = 2000 * 1024 * 1024

where the number 2000 is the memory allocation in MB.

Also, when connecting wirelessly and setting a very high speed, clients may lose their connection,
which may give you away. It is recommended to run ping in a neighboring terminal to some domain resource, and if
these pings start to get lost when the program is running, then the point cannot cope with the flow of a large number of small packets.

Usage example:

python3 multi_nmaputka_scaner.py -r read_ip_file -f save_file -s 100

where:

-the r file from which the ip addresses will be read

-f is the keyword for the session from which the files will start, where the result will be saved

-s is the number of parallel processes to be started (50 by default)

-c - get only ip addresses at the output, without output of the nmap result (optional parameter)