import time

from specgen.generate import main

if __name__ == "__main__":
    t1 = time.time()
    main()
    print("Completed generation for all volcanos in", time.time() - t1)
