import random
import signal
import sys
import threading
from threading import Thread
from time import sleep

from utils.logger import logger


def work(s):
    print(threading.currentThread().getName()+"->"+ s)
    s = random.randint(1,10)
    print(threading.currentThread().getName()+"sleep->"+ str(s))
    sleep(s)
    print(threading.currentThread().getName()+"end")
def main():
    threads=[]
    for i in range(5):
        threads.append(Thread(target=work, args=('hello world',)))
    for t in threads:
        t.setDaemon(True)
        t.start()
    #join()方法是阻塞的，会等待线程执行完毕再执行主线程
    for t in threads:
        t.join()
def exit_app(signal_, frame):
    logger.info("正在退出...")
    sys.exit()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_app)
    main()

    print("main end")