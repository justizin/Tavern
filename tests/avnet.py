import random
import timeit
# This a literal translation of the AVnet.
# I used inclusive ranges and lists because the original paper did, and I wanted to make sure I followed.

def irange(param1,param2=None,param3=None):
    """Inclusive range function"""
    if param2 is None and param3 is None:
        # 1 argument passed in
        return range(param1+1)
    elif param3 is None:
        # 2 args
        return range(param1,param2+1)
    else:
        return range(param1,param2+1,param3)

class list1(list):
    """One-based version of list."""

    def _zerobased(self, i):
        if type(i) is slice:
            return slice(self._zerobased(i.start),
                         self._zerobased(i.stop), i.step)
        else:
            if i is None or i < 0:
                return i
            elif not i:
                raise IndexError("element 0 does not exist in 1-based list")
            return i - 1

    def __getitem__(self, i):
        return list.__getitem__(self, self._zerobased(i))

    def __setitem__(self, i, value):
        list.__setitem__(self, self._zerobased(i), value)

    def __delitem__(self, i):
        list.__delitem__(self, self._zerobased(i))

    def __getslice__(self, i, j):
        return list.__getslice__(self, self._zerobased(i or 1),
                                 self._zerobased(j))

    def __setslice__(self, i, j, value):
        list.__setslice__(self, self._zerobased(i or 1),
                          self._zerobased(j), value)

    def index(self, value, start=1, stop=-1):
        return list.index(self, value, self._zerobased(start),
                          self._zerobased(stop)) + 1

    def pop(self, i):
        return list.pop(self, self._zerobased(i))



def small_prime_generator(max=1000):
    """
    Generate every small prime up to `max`
    """
    prime = []
    notprime = []
    for i in range(2,max):
        if i not in notprime:
            prime.append(i) 
            for j in range(i,max,i):
                notprime.append(j)
    return prime

def miller_rabin(n,rounds=64):
    """
    True if `n` passes `k` rounds of Miller-Rabin.
    """
    if n < 2:
        return False
    
    # Eliminate the easy ones with a table
    global small_primes

    if not 'small_primes' in globals():
        small_primes = small_prime_generator(50)
    for p in small_primes:
        if n % p == 0:
            return False

    # Do Miller-Robin (40 rounds) to determine likely prime
    s = n-1
    r = 1
    while s % 2 == 0:
        s //= 2
        r +=1 

    for _ in range(rounds):
        a = random.SystemRandom().randrange(2, n - 1)
        x = pow(a, s, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def gen_prime(bits):
    prime = False
    while prime is not True:
        number = random.SystemRandom().getrandbits(bits)
        # No evens
        if not number % 2:
            number = number +1
        prime = miller_rabin(number)
    return int(number)

def gen_dh_group(bits):
    """Generate a group of primes for DH style exchange"""
    while 1:
        # Generate random prime q until 2q+1 is also a prime. 
        q = int(gen_prime(bits))
        p = (2 * q) + 1
        if miller_rabin(p):
            # A generator of 2 will provide just as much security as any other, and is cheaper.
            g = 2
            break
    return (p, q, g)

def dh_test(bits=100,a=None,b=None,p=None,g=None):
    """Test DH exchange"""
    if p == None:
        p,q,g = gen_dh_group(bits)
    if g == None:
        g = 2

    if a is None:
        alice_priv = random.SystemRandom().getrandbits(bits)
    else:
        alice_priv = a

    alice_pub = G(g, alice_priv, p)

    if b is None:
        bob_priv = random.SystemRandom().getrandbits(bits)
    else:
        bob_priv = b
    bob_pub = G(g, bob_priv, p)

    alice_shared_secret = pow(bob_pub, alice_priv, p)
    bob_shared_secret = pow(alice_pub, bob_priv, p)

    if alice_shared_secret == bob_shared_secret:
        print(alice_shared_secret)
        print("Match")
    else:
        print("No Match")

def main():

    # number of participants
    n = 20
    bits = 100

    # Every participant agrees on a Generator function
    p,q,g= gen_dh_group(100)
    G = lambda x: pow(g,x,p)

    # Every participant gets a number   
    x = list1()

    ### ROUND 1
    # Loop through all participants (i)
    for i in irange(1,n):
        
        # Each participant selects a random number.
        R = random.SystemRandom().getrandbits(bits)
        # Store this for each participant as x
        x.append(R)

    ### When this round finishes, each participant computes
    for i in irange(1,n):

        numerator = 1
        for j in range(1,i-1):
            numerator *= G(x[j])
     #   print("n: " + str(numerator))

        denominator = 1
        for j in range(i+1,n):
            denominator *= G(x[j])           
     #   print("d: " + str(denominator))

        gyi = numerator//denominator
        print("gyi " + str(gyi))



    # Every participant broadcasts a value gciyi and a knowledge proof for ci, where ci is either xi or a random value 







    #print(small_primes)
if __name__ == "__main__":
    main()