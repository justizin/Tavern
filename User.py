import os
import json
from Envelope import *
import time
from keys import *
from collections import OrderedDict
import pymongo
from Server import server
import scrypt
import base64
from lockedkey import lockedKey
from TavernUtils import memorise
from ServerSettings import serversettings
import time
import datetime
import math
from keys import Keys

class User(object):

    def __init__(self,pubkey=None):
        self.UserSettings = {}
        self.UserSettings['followedUsers'] = []
        self.UserSettings['followedTopics'] = []
        self.UserSettings['status'] = {}
        self.UserSettings['keys'] = {}
        self.UserSettings['keys']['master'] = None
        self.passkey = None
        self.Keys = {}
        self.Keys['posted'] = []
        self.Keys['master'] = None

    def get_current_commkey(self):
        """
        Gets the current communication key.
        If one does not exist, it creates one.
        """
        print("nope!")


    def randstr(self, length):
        # Random.randint isn't secure, use the OS urandom instead.
        return ''.join(chr(int.from_bytes(os.urandom(1), 'big')) for i in range(length))

    def hash_password(self, password, maxtime=5, datalength=64):
        pword = scrypt.encrypt(
            self.randstr(datalength), password, maxtime=maxtime)
        return base64.b64encode(pword).decode('utf-8')

    def verify_password(self, guessed_password, hashed_password=None, maxtime=50):
        try:
            if hashed_password is None:
                hashed_password = self.passkey
            pword = base64.b64decode(hashed_password.encode('utf-8'))
            scrypt.decrypt(pword, guessed_password, maxtime)
            return True
        except scrypt.error:
            return False

    @memorise(parent_keys=['Keys.master.pubkey'], ttl=serversettings.settings['cache']['user-note']['seconds'], maxsize=serversettings.settings['cache']['user-note']['size'])
    def getNote(self, noteabout):
        """
        Retrieve any note by user A about user B
        """
        # Make sure the key we're asking about is formatted right.
        # I don't trust myself ;)

        key = Keys(pub=noteabout)
        noteabout = key.pubkey
        # Retrieve the note from mongo
        note = server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if note is not None:
            return note['note']
        else:
            if noteabout == self.Keys['master'].pubkey: 
                # I'm asking about myself, and I haven't set a note yet.
                return "This is you!"
            else:
                return None

    def setNote(self, noteabout, note=""):
        # Format the Key.
        key = Keys(pub=noteabout)
        noteabout = key.pubkey

        newnote = {"user": self.Keys['master'].pubkey, "noteabout":
                   noteabout, "note": note}

        # Retrieve any existing note, so that the _id is the same. Then, we'll gut it, and put in our own values.
        newnote = server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if newnote is None:
                newnote = {"user": self.Keys['master'].pubkey,
                           "noteabout": noteabout, "note": note}
        newnote['note'] = note
        server.db.unsafe.save('notes', newnote)
        self.getNote(noteabout=noteabout, forcerecache=True)

    @memorise(parent_keys=['Keys.master.pubkey'], ttl=serversettings.settings['cache']['user-trust']['seconds'], maxsize=serversettings.settings['cache']['user-trust']['size'])
    def gatherTrust(self, askingabout, incomingtrust=250):
        """
        Return how much I trust a given ID, rather than a given post.
        This is determined by several factors, but the base algorithm is:
            [Keys and Spam Ranking]
            [Have I rated this person]
            [Have any friends rated this person]
            [Have any FOF or FOFOF rated this person]
            [Each generation of friends gets their trust multiplied by .4, since you trust them less and less]
        """
        # Ensure we have proper formatting for the key we're examining, so we find it in the DB.
        key = Keys(pub=askingabout)
        askingabout = key.pubkey

        # Our opinion of everyone starts off Neutral
        trust = 0

        # Set the maximum amount of trust we can return.
        # This is set to 40% of incoming - Incoming starts at 250, to ensure that this goes to 100 for myself.
        maxtrust = .4 * incomingtrust

        # We trust ourselves implicitly
        if askingabout == self.Keys['master'].pubkey:
            server.logger.info("I trust me.")
            return round(incomingtrust)

        # Don't recurse forever, please.
        # Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0 etc
        if incomingtrust <= 2:
            return 0

        # Query mongo to retrieve the most recent rating for a specific user.
        myvote = server.db.unsafe.find_one(collection='envelopes', query={"envelope.payload.class": "usertrust", "envelope.payload.trusted_pubkey": str(askingabout), "envelope.payload.trust": {"$exists": "true"}, "envelope.local.author.pubkey": str(self.Keys['master'].pubkey)}, sortkey="envelope.local.time_added", sortdirection='descending')

        if myvote:
            # If I directly rated this user, Mazel tov, that was easy.
            server.logger.info("I rated this user directly.")
            trust = int(myvote['envelope']['payload']['trust'])

        else:
            # If we didn't directly rate the user, let's see if any of our friends have rated him.

            # First, let's get a list of the friends we trust
            alltrusted = server.db.unsafe.find('envelopes', {"envelope.payload.class": "usertrust", "envelope.payload.trust": {"$gt": 0}, "envelope.local.author.pubkey": self.Keys['master'].pubkey})
            combinedFriendTrust = 0
            friendcount = 0

            # Now, iterate through each of those people, and see if they rated him. Check THEIR friends.
            # This will be slow for the first search, but the function uses a decorator for caching.
            for trusted in alltrusted:
                friendcount += 1
                # Load in our friend from the DB.
                u = User()
                u.load_mongo_by_pubkey(
                    trusted['envelope']['payload']['trusted_pubkey'])
                # How much do we trust our Friend...
                # We're only going to be here if we directly rated them, which set it out at 100
                # But if they're from a bad neighborhood, or if they constantly recommend people we downvote, we might decide we don't like them anymore.
                # That's why we want to weigh their recomendation by how much we trust them.
                amountITrustThisFriend = u.gatherTrust(askingabout=trusted['envelope']['payload']['trusted_pubkey'],incomingtrust=maxtrust)
                amountMyFriendTrustsAskingAbout = u.gatherTrust(
                    askingabout=askingabout, incomingtrust=maxtrust)

                # I can never trust my friends unusual amounts.
                if amountITrustThisFriend > 100:
                    amountITrustThisFriend = 100
                if amountITrustThisFriend < 1:
                    amountITrustThisFriend = 1

                combinedFriendTrust += round((amountITrustThisFriend/100) * amountMyFriendTrustsAskingAbout)

            if friendcount > 0:
                trust = combinedFriendTrust / friendcount
            server.logger.info("total friend average" + str(trust))

        # Ensure that this element of the trust doesn't go out of range, and unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)


        # OK, so now we have a rating for this user, either directly or indirectly.
        # Let's add other characteristics.



        # For instance, If we've upvoted this guy, that should weigh in, somewhat.
        # We'll weigh the vote by log2, to discourage vote-farming.
        ratingtally = 0
        allratings = server.db.unsafe.find('envelopes', {"envelope.payload.class": "messagerating", "envelope.payload.rating": {"$exists": "true"}, "envelope.local.regardingAuthor": askingabout})
        for rating in allratings:
            ratingtally += rating['envelope']['payload']['rating']
        
        # Reduce it using log2, carefully saving the direction.
        if ratingtally < 0:
            weighted = math.log2(ratingtally * -1) * -1
        elif ratingtally > 0:
            weighted = math.log2(ratingtally)
        else:
            weighted = 0

        trust += weighted

        # Ensure that this element of the trust doesn't go out of range, and unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)


        # We should also reduce their trust everytime we disagree with a recommendation.
        # We still like them, but we don't trust their judgement.
        ## TODO - How can we do this without spending ALL the CPU?


        # Add up the trusts from our friends, and cap at MaxTrust
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)

        trust = round(trust)
        print("trust is :" + str(trust))
        return trust

    def translateTrustToWords(self, trust):
        if trust == 250:
            return "are"
        if trust > 75:
            return "strongly trust"
        elif trust > 50:
            return "moderately trust"
        elif trust > 10:
            return "slightly trust"
        elif trust > -10:
            return "are neutral toward"
        elif trust > -50:
            return "slightly distrust"
        elif trust > -75:
            return "moderately distrust"
        else:
            return "strongly distrust"

    @memorise(parent_keys=['Keys.master.pubkey'], ttl=serversettings.settings['cache']['message-ratings']['seconds'], maxsize=serversettings.settings['cache']['message-ratings']['size'])
    def getRatings(self, postInQuestion):
        """
        Get the ratings of a specific message
        """
        #Move this. Maybe to Server??
        allvotes = server.db.unsafe.find('envelopes', {"envelope.payload.class": "messagerating", "envelope.payload.rating": {"$exists": "true"}, "envelope.payload.regarding": postInQuestion})
        combinedrating = 0
        for vote in allvotes:
            author = vote['envelope']['local']['author']['pubkey']
            rating = vote['envelope']['payload']['rating']
            authorTrust = self.gatherTrust(askingabout=author)

            # Now that we know how much we trust the author, pay attention to their rating in proportion to how much we trust them.
            if authorTrust > 0:
                authorPCT = authorTrust/100
                combinedrating += rating *  authorPCT

        # Stamp based ratings give a baseline, like SpamAssassin.
        e = server.db.unsafe.find_one('envelopes',
                                      {"envelope.local.payload_sha512": postInQuestion})

        if e is not None:
            if 'stamps' in e['envelope']:
                stamps = e['envelope']['stamps']
                for stamp in stamps:
                    # if it was posted directly to OUR server, we can ip limit it, give it a +1
                    if stamp['class'] == "origin":
                        if stamp['pubkey'] == server.ServerKeys.pubkey:
                            combinedrating += 1

        return combinedrating

    def followTopic(self, topic):
        if topic not in self.UserSettings['followedTopics']:
            self.UserSettings['followedTopics'].append(topic)

    def unFollowTopic(self, topic):
        # Compare the lowercase/sorted values
        for followedtopic in self.UserSettings['followedTopics']:
            if server.sorttopic(followedtopic) == server.sorttopic(topic):
                self.UserSettings['followedTopics'].remove(followedtopic)


                
    def generate(self,GuestKey=True,password=None,email=None, username=None):
        """
        Create a Tavern user, filling in any missing information for existing users.
        Only creates keys if asked to.
        """

        # Ensure that these values are filled in.
        # Either by Saved values, Passed-in values, or by Null objects.

        # Keep track of if anything changed.
        anychanges = False

        if username is not None:
            self.UserSettings['username'] = username
            anychages = True

        elif not 'username' in self.UserSettings:
            self.UserSettings['username'] = "Anonymous"
            anychages = True

        if email is not None:
            self.UserSettings['email'] = email
            anychages = True

        elif not 'email' in self.UserSettings:
            self.UserSettings['email'] = "email@example.org"
            anychages = True

        if password is not None and self.passkey is None:
            self.passkey = self.hash_password(password)
            anychages = True

        if not 'guest' in self.UserSettings['status']:
            self.UserSettings['status']['guest'] = True
            anychages = True

        if not 'setpassword' in self.UserSettings['status']:
            self.UserSettings['status']['setpassword'] = None
            anychages = True

        # Ensure we have a valid keys, one way or another.
        # If GuestKey is true, then use the server default accts.
        # Otherwise, make the keys.

        if self.Keys['master'] is None:
            # Save if we're using the GuestKey or not.
            if GuestKey == True:
                    self.Keys = server.guestacct.Keys   
                    self.UserSettings['status']['guest']  = True
            else:
                print("Generating a LockedKeys")
                self.Keys['master'] = lockedKey()
                self.Keys['master'].generate(password=password)                
                self.UserSettings['status']['guest']  = False

            anychages = True

        # Ensure we have a valid/current public posted key.
        if self.UserSettings['status']['guest'] is not True:
            # Set key to false, disprove assertion later.
            validcommkey = False
            # Make sure our Posted keys are in good shape.
            if len(self.Keys['posted']) > 0:
                # Sort the keys that we've already posted, highest expires first.
                self.Keys['posted'].sort(key=lambda e: (e.expires),reverse=True)
                # Calculate a time 2 weeks in the future
                futuretimedate = datetime.datetime.now() + datetime.timedelta(days=14)
                futuredate =  time.mktime(futuretimedate.timetuple())            
                curkey = self.Keys['posted'][-1]
                if curkey.expires > futuredate:
                    validcommkey = True

            # Either we have no key, or an old one.
            if validcommkey == False:
                print("Generating new posted key")
                newkey = lockedKey()
                newkey.generate(passkey = self.passkey)   
                # Calculate a time 60 days in the future
                futuretimedate = datetime.datetime.now() + datetime.timedelta(days=60)
                futuredate =  time.mktime(futuretimedate.timetuple())
                newkey.expires = futuredate
                self.Keys['posted'].append(newkey)
                anychages = True


        if not 'time_created' in self.UserSettings:
            self.UserSettings['time_created'] = int(time.time())
            anychages = True

        if not 'display_useragent' in self.UserSettings:
            self.UserSettings['display_useragent'] = False
            anychages = True

        if not 'theme' in self.UserSettings:
            self.UserSettings['theme'] = 'default'
            anychages = True

        if not 'followedTopics' in self.UserSettings:
            self.UserSettings['followedTopics'] = []
            anychages = True

        if not 'allowembed' in self.UserSettings:
            self.UserSettings['allowembed'] = 0
            anychages = True

        if self.UserSettings['followedTopics'] == []:
            self.followTopic("StarTrek")
            self.followTopic("Python")
            self.followTopic("Egypt")
            self.followTopic("Funny")
            anychages = True

        if not 'maxposts' in self.UserSettings:
            self.UserSettings['maxposts'] = 100
            anychages = True

        if not 'maxreplies' in self.UserSettings:
            self.UserSettings['maxreplies'] = 100
            anychages = True

        # Set Friendlyname to most recent post, or Anonymous for lurkers
        if not 'friendlyname' in self.UserSettings:
            if self.UserSettings['status']['guest'] == False:
                # They're registered, they may have posted.
                posts = server.getUsersPosts(self.Keys['master'].pubkey)
                if len(posts) > 0:
                    self.UserSettings['friendlyname'] = posts[0].dict['envelope']['local']['author']['friendlyname']
                    anychages = True
            if not 'friendlyname' in self.UserSettings:
                self.UserSettings['friendlyname'] = 'Anonymous'
                anychages = True

        if not 'include_location' in self.UserSettings:
            self.UserSettings['include_location'] = False
            anychages = True

        if not 'ignoreedits' in self.UserSettings:
            self.UserSettings['ignoreedits'] = False
            anychages = True

        if not 'author_wordhash' in self.UserSettings:
            self.UserSettings['author_wordhash'] = server.wordlist.wordhash(self.Keys['master'].pubkey)
            anychages = True

        return anychanges


    def changepass(self, oldpasskey, newpassword):
        """
        Change the User's password
        """
        # Re-encrypt our Privkey
        
        if self.Keys['master'].changepass(oldpasskey=oldpasskey, newpassword=newpassword):    
            self.passkey  = self.hash_password(newpassword)
            self.UserSettings['lastauth'] = int(time.time())
            self.UserSettings['status']['setpassword'] = int(time.time())
            self.savemongo()
        else:
            return False


    def presave_clean(self):
        """
        Ensure our keys are saved to the userdict for later restore, and remove sensetive info
        """
        if self.Keys.get('master'):
            if not self.UserSettings['keys'].get('master'):
                self.UserSettings['keys']['master'] = {}
            self.UserSettings['keys']['master']['pubkey'] = self.Keys['master'].pubkey

            self.UserSettings['keys']['master']['encryptedprivkey'] = self.Keys['master'].encryptedprivkey
            self.UserSettings['keys']['master']['generated'] = int(time.time())
            self.UserSettings['keys']['master']['expires'] = None
            self.UserSettings['keys']['master']['privkey'] = None

        self.UserSettings['keys']['posted'] = []
        for key in self.Keys['posted']:

                keydict = {}
                keydict['pubkey'] = key.pubkey
                keydict['encryptedprivkey'] = key.encryptedprivkey
                keydict['generated'] = key.generated
                keydict['expires'] = key.expires
                self.UserSettings['keys']['posted'].append(keydict)

        self.UserSettings['passkey'] = None
        self.UserSettings['_id'] = self.Keys['master'].pubkey


    def restore_keys(self):
        """
        After being loaded in, re-create out key objects.
        """
        # Restore our master key
        if self.UserSettings['keys'].get('master') is not None:
            if 'encryptedprivkey' in self.UserSettings['keys']['master']:
                self.Keys['master'] = lockedKey(pub=self.UserSettings['keys']['master']['pubkey'], encryptedprivkey=self.UserSettings['keys']['master']['encryptedprivkey'])
                self.Keys['master'].generated =  self.UserSettings['keys']['master']['generated']
                self.Keys['master'].expires = self.UserSettings['keys']['master']['expires']
                server.logger.info("Reconstructed with encryptedprivkey")
            else:
                # If we just have a pubkey string, do the best we can.
                if self.Keys['master'] is not None:
                    if self.Keys['master'].get('pubkey'):
                        self.Keys['master'] = Keys(pub=self.UserSettings['keys']['master']['pubkey'])
                        self.Keys['master'].generated = self.UserSettings['keys']['master'].get('generated')
                        self.Keys['master'].expires = self.UserSettings['keys']['master'].get('expires')
                        server.logger.info("reconstructed user without privkey")
                
        # Restore any Posted communication keys.
        for key in self.UserSettings['keys'].get('posted',[]):
            lk = lockedKey(pub=key['pubkey'],encryptedprivkey=key['encryptedprivkey'])
            lk.generated =  key['generated']
            lk.expires = key['expires']
            self.Keys['posted'].append(lk)

    def load_string(self, incomingstring):
        self.UserSettings = json.loads(incomingstring, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        # Sort our Posted keys.
        self.Keys['posted'].sort(key=lambda e: (e.expires),reverse=True)
        self.restore_keys()
        self.generate()

    def load_file(self, filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.load_string(filecontents)

    def savefile(self, filename=None):
        if filename is None:
            filename = self.UserSettings['username'] + ".TavernUser"

        self.presave_clean()
        filehandle = open(filename, 'w')
        filehandle.write(json.dumps(self.UserSettings, separators=(',', ':')))
        filehandle.close()

    def load_mongo_by_pubkey(self, pubkey):
        """
        Returns a user object for a given pubkey
        """

        # Get Formatted key for searching.
        tmpkey = Keys(pub = pubkey)
        user = server.db.safe.find_one('users',
                                       {"keys.master.pubkey": tmpkey.pubkey})
        if user is not None:
            # If we find a local user, load in their priv and pub keys.
            self.load_string(json.dumps(user))
        else:
            # If the user doesn't exist in our service, he's only someone we've heard about.
            # We won't know their privkey, so load the pubkey, and then reload the user
            print("Can't find user by pubkey. Using pub-only.")
            self.UserSettings['keys']['master']['pubkey'] = pubkey
            self.load_string(json.dumps(self.UserSettings))

    def load_mongo_by_username(self, username):
        #Local server Only
        user = server.db.safe.find_one('users',
                                       {"username": username})
        # If we're loading by username, it means you logged in.  
        # Ensure settings are up to date

        if self.generate():
            self.savemongo()

        self.load_string(json.dumps(self.UserSettings))

    def savemongo(self):
        self.presave_clean()
        server.db.safe.save('users', self.UserSettings)
