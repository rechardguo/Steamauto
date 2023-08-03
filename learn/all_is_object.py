
def wrapper(fun):
    def inner(*args, **kwargs):
        print("before")
        fun(*args, **kwargs)
        print("after")
    return inner

if __name__ == '__main__':
    wrapper(lambda x: print(x))(1)
