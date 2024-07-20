Данный код позволит провести icmp сканирование сети.

Скорость зависит от типа Вашего подключения и мощности железа. Идея заключается в большом количестве параллельных icmp
запросов. 

Предупреждения!

Так же при подключении по беспроводной сети и выставлении очень большой скорости у клиентов может пропасть подключение,
что может выдать Вас. Рекомендуется запустить ping в соседнем терминале до какого нибудь доменного ресурса, и, если при
работе программы эти ping-и начинают теряться, значит точка не справляется с потоком большого количества маленьких пакетов. 

Пример использования:

```commandline
python3 multi_pingutka_scaner.py -r 192.168.0.0-192.168.255.255 -f file_save -s 100
```

где:

-r - диапазон ip адресов

-f - файл, куда будет сохранен результат (будет заполнен после окончания сканирования)

-s - количество параллельных потоков, которые будут запущены (по умолчанию 100)

########################################################################################################################

This code will allow you to perform an icmp scan of the network.

The speed depends on the type of your connection and the power of the hardware. The idea is to have a large number of 
parallel icmp requests. 

Warnings!

Also, when connecting wirelessly and setting a very high speed, customers may lose their connection,
which could give you away. It is recommended to run ping in a neighboring terminal to some domain resource, and if
these pings start to get lost when the program is running, then the point cannot cope with the flow of a large number of
small packets. 

Usage example:

```commandline
python3 ping_scaner.py -r 192.168.0.0-192.168.255.255 -f file_save -s 100
```

where:

-r is the range of ip addresses

-f - file where the result will be saved (it will be filled in after the scan is completed)

-s is the number of parallel thread to be started (100 by default)
