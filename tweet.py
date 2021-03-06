from utils import *
from queries import * 

def compose_tweet(session, menu_func=None, replyto=None):
    """ Generates a new tweet and inserts it into the database
    Also inserts any hashtags into hashtags and mentions tables

    :param session: Session object 
    :param menu_func: the function to return to 
    :param replyto (optional): the user id of who the tweet is replying to
    """
    new_tweet = create_tweet(session, menu_func, replyto)
 
    confirm = validate_yn("Confirm tweet? y/n: ", session)
    if confirm in ["n", "no"]:
        print("Tweet cancelled.")
        return None if menu_func is None else menu_func() 
             
    insert_tweet(session.get_conn(), new_tweet.get_values())
    new_tweet.insert_terms()

    print("Tweet %d created - %s." % (new_tweet.tid(), new_tweet.tdate()))
    print("Hashtags mentioned: %s" % (new_tweet.get_terms()))
    press_enter(session)

def create_tweet(session, menu_func, replyto):
    """Gets info for new tweet and creates new Tweet object

    :param session: Session object
    :param menu_func: function to return to if user quits
    :param replyto: id of user to replyto or None
    """
    text = validate_str("Enter tweet: ", session, menu_func=menu_func, null=False)
    if len(text) > 80:
        print("Tweet is too long. Must be 80 characters or less.")
        return create_tweet(session, menu_func, replyto)
  
    print_border(thick=False)
    writer = session.get_username()
    tid = generate_tid(session.get_conn())
    date = TODAY
    replyto = replyto
    rt_user = None
    data = [tid, writer, date, text, replyto, rt_user]
    new_tweet = Tweet(session, data)
    new_tweet.display(result="Tweet")
    print_border(thick=False)
    new_tweet.set_terms()

    if not new_tweet.valid_terms():
        return create_tweet(session, menu_func, replyto)
    
    return new_tweet

   
def generate_tid(conn):
    """Generates a new unique tweet id
    
    :param conn: session connection
    """
    curs = conn.cursor()
    select(curs, 'tweets')
    new_tid = len(curs.fetchall()) + 1
    
    while tid_exists(curs, new_tid): 
        new_tid += 1
    curs.close()

    return new_tid


def search_tweets(session):
    """Match tweets to user's keywords

    :param session: session connection
    """
    search_input = validate_str("Enter keywords for tweet search: ", session, session.home, null=False)
    s_tweets = TweetSearch(session, search_input)
    s_tweets.get_search_tweets()
    return s_tweets 


class Tweet:

    def __init__(self, session, data):
        """ Represents a single tweet, helps to display tweets to console
       
        param session: Twitter object 
        param data: row values from tweets table corresponding to columns 
        """
        self.session = session
        self.conn = session.get_conn() 
        self.curs = session.get_curs() 
        self.user = session.get_username() 

        self.id = data[0]
        self.writer = data[1]
        self.date = data[2]
        self.text = data[3].rstrip()
        self.replyto = data[4]

        if len(data) > 5: 
            self.rt_user = data[5]
        else:
            self.rt_user = None

        if self.replyto:
            self.reply_user = get_user_from_tid(self.curs, self.replyto)
            self.reply_name = get_name(self.curs, self.reply_user)
            self.reply_text = get_text_from_tid(self.curs, self.replyto)

        self.date_str = convert_date(self.date)
        self.rep_cnt = None 
        self.ret_cnt = None 
        self.writer_name = get_name(self.curs, self.writer)
        
        self.terms = get_hashtags(self.curs, self.id)
        if self.terms is None: 
            self.terms = []

    def author(self):
        """Return the tweet writer"""
        return self.writer

    def reply_tweet(self):
        """Return the replyto tweet id"""
        return self.replyto

    def replyer(self):
        """Return the replyto user id"""
        return self.reply_user

    def retweeter(self):
        """Return the id of retweeter"""
        return self.rt_user

    def tdate(self):
        """Return the tweet date"""
        return self.date_str

    def tid(self):
        """Return the tweet id"""
        return self.id

    def get_text(self):
        """Get the tweet text"""
        return self.text

    def tweet_menu(self):
        """Displays options to reply or retweet a tweet after it has 
        been selected
        Returns the selected option from the tweet menu
        """
        choices = ["Reply", "Retweet", "Go back", "Search for other tweets", "Home", "Logout"]
        print_border(thick=True)
        display_selections(choices)

        return choices

    def display(self, index=None, rt_user=None, result="Result", width=65):
        """ Displays basic info on a tweet
        Used for first screen after login or a tweet search
      
        :param index (optional): tweet number (1-5)  
        :param rt_user (optional): user id of the user who retweeted this tweet
        :param result (optional): row title
        :param width (optional): row width for text
        """
        if index is not None: 
            tweet_index = "%s %d" % (result, index + 1)
        else:
            tweet_index = "%s %d" % (result, self.id)

        # Set up formatting variables
        col1_width = len(tweet_index) + 1
        col2_width = BORDER_LEN - col1_width - 3
        blank = " " * col1_width 
      
        # Add reply user id at beginning of text 
        if self.replyto is not None:
            text_str = "@%s %s" % (self.reply_user, self.text)
        else:
            text_str = self.text

        text1, text2 = self.split_text(text_str, max_width=width)
        date_line = "%s" % (self.date_str)
        info = "%s @%d - %s" % (self.writer_name, self.writer, date_line)
 
        # Format column 1 for tweet numbers
        line1_1 = "{:{width}}".format(tweet_index, width=col1_width)

        # Format lines for display tweet
        line1_2 = "  {:{width}}".format(info, width=col2_width)
        line2_2 = "  {:{width}}".format(text1, width=col2_width)
        line3_2 = "  {:{width}}".format(text2, width=col2_width)
        line4_2 = "  {:{width}}".format(" ", width=col2_width)

        # Adjust lines if tweet is a retweet
        if rt_user is not None:
            user_name = get_name(self.curs, rt_user)
            retweeted = "%s Retweeted" % user_name
            line4_2 = line3_2
            line3_2 = line2_2
            line2_2 = line1_2
            line1_2 = "  {:{width}}".format(retweeted, width=col2_width)

        # Print to the console
        print_string(line1_1 + line1_2)
        print_string(blank + line2_2)
        if line3_2[2] != " ": 
            print_string(blank + line3_2)
        if line4_2[2] != " ":
            print_string(blank + line4_2)

    def split_text(self, text, max_width=65):
        """Splits up tweets text into 2 separate lines if too long

        :param text: text string
        :param max_width: row width of text
        """
        space_index = -1
        text = text + " "
        text1 = text
        text2 = ""

        if len(text) > max_width:
            space_index = text.find(' ', max_width-5)
        
        if space_index >= max_width:
            space_index = 0

            i = max_width
            while text[i] != ' ': 
                i -= 1
            space_index = i
        
        if space_index > 0:    
            text1 = text[:space_index]
            text2 = text[space_index + 1:]

        return (text1, text2)

    def display_stats(self):
        """ Displays statistics on a tweet after the tweet has been selected
        From here, the user can decide to reply/retweet the tweet.
        """
        print_newline() 
        print_border(thick=True)
        print_string("Tweet Statistics".upper())
        print_border(thick=True, sign='|')

        # Print tweet text first
        text1, text2 = self.split_text(self.text, max_width=75)
        print_string(text1)
        if len(text2) > 1: 
            print_string(text2)
        print_newline(no_border=False)

        # Tweet stats
        self.rep_cnt = get_rep_cnt(self.curs, self.id)
        self.ret_cnt = get_ret_cnt(self.curs, self.id)
        print_string("Tweet ID: %d" % (self.id))
        print_string("Written by: %s @%d" % (self.writer_name, self.writer)) 
        print_string("Posted: %s" % (self.date_str))
        print_string("Number of replies: %s" % (self.rep_cnt))
        print_string("Number of retweets: %s" % (self.ret_cnt))

        # Display what the tweet is replying to 
        if (self.replyto):
            rep_str = "%s @%d - %s" % (self.reply_name, self.reply_user, self.reply_text)
            text1, text2 = self.split_text(rep_str)
            print_string("In reply to: %s" % (text1))
            if len(text2) > 1:
                print_string(text2)
        else:
            print_string("In reply to: None")

        # Display menu to follow, etc. 
        choices = self.tweet_menu()
        choice = validate_num(SELECT, self.session, self.session.home, size=len(choices))
        return choices[choice-1]

    def reply(self, menu_func=None):
        """Reply to the Tweet

        :param menu_func: return point if user decides to cancel reply
        """
        compose_tweet(self.session, menu_func, replyto=self.id)

    def retweet(self, menu_func=None):
        """Allows logged in user to retweet a selected tweet

        :param menu_func: return point if user decides to cancel retweet
        """
        if already_retweeted(self.curs, self.user, self.id):
            print("You already retweeted this tweet.")
            press_enter(self.session) 
            return None if menu_func is None else menu_func()
            
        print_border(thick=False)
        self.display(rt_user=self.user)
        print_border(thick=False)

        confirm = validate_yn("Confirm retweet? y/n: ", self.session)
        if confirm in ["n", "no"]:
            print("Retweet cancelled.")
            
        else:
            print("Retweeted - %s" % (convert_date(TODAY)))
            data_list = [self.user, self.id, TODAY]
            insert_retweet(self.conn, data_list)

            press_enter(self.session)

    def get_values(self):
        """Returns a list of tid, writer, tdate, text, and replyto"""
        return [self.id, self.writer, self.date, self.text, self.replyto]

    def get_terms(self):
        """Returns the list of hashtag terms for the tweet"""
        return self.terms

    def set_terms(self):
        """Finds the hashtags in a tweet and returns the terms""" 
        hashtags = self.find_hashtags() 

        for tag in hashtags:
            term = self.extract_term(tag).lower()
            if len(term) > 0:
                self.terms.append(term)
        
    def insert_terms(self):
        """Inserts all hashtag terms into the hashtags table"""
        for term in self.terms:
            if not hashtag_exists(self.curs, term):
                insert_hashtag(self.conn, term)      
 
            if not mention_exists(self.curs, self.id, term):
                insert_mention(self.conn, [self.id, term])
 
    def valid_terms(self):
        """Returns True if all terms do not exceed restriction length"""
        for term in self.terms:
            if len(term) > 10:
                print("%s is too long. Must be 10 characters or less.\n" % (term))
                self.terms = []
                return False
        return True

    def get_nohash(self):
        """Return tweet text without the hashtags"""
        text_str = self.text.lower()
        for word in self.terms:
            word = '#' + word
            text_str = text_str.replace(word, '')
        return text_str

    def extract_term(self, index):
        """Gets the hashtag term in the tweet based on the index
        
        :param index: the index of the hashtag in the tweet text
        Returns the hashtag term
        """
        if index + 1 >= len(self.text):
            return "" 

        i = index
        while i < len(self.text) - 1 and self.text[i + 1].isalnum():
            i += 1

        if i + 1 == len(self.text):
            return self.text[index+1:]
        else:
            return self.text[index+1:i+1]

    def find_hashtags(self):
        """ Returns a list of all indexes of found hashtags"""
        index_list = []
        for i, ch in enumerate(self.text):
            if ch == '#':
                index_list.append(i)
        return index_list

class TweetSearch:

    def __init__(self, session, keywords=''):
        """Can be used for getting tweets of users being 
        followed or searching for specific tweets based on keywords
         
        param session: database session connection
        param keywords: input string for tweet search 
        """ 
        self.session = session
        self.conn = session.get_conn() 
        self.user = session.get_username() 
        self.tweetCurs = self.session.get_curs() 
        self.all_tweets = []
        self.tweets = []
        self.more_exist = False
        self.tweet_index = 5
        self.rows = None
        self.searched = keywords
        self.keywords = convert_keywords(keywords)
 
        if len(self.keywords) > 0: 
            self.category = "TweetSearch"
            self.search = True
        else:
            self.category = "Home"
            self.search = False

    def is_search(self):
        """Return True if category is TweetSearch""" 
        return self.search

    def get_category(self):
        """Return either TweetSearch or Home"""
        return self.category 
 
    def is_first_page(self):
        """Return True if the current tweets are the first 5 tweets"""
        return self.tweet_index <= 10 

    def get_searched(self):
        """Return user's search keywords"""
        width = 50
        if len(self.searched) > width:
            return self.searched[:width] + "..."
        else:
            return self.searched

    def reset(self):
        """Reset the home page to the first 5 tweets"""
        self.all_tweets = []
        self.tweets = []
        self.more_exist = False
        self.rows = None
        self.tweet_index = 5

        if not self.search: 
            self.get_user_tweets()
        else:
            self.get_search_tweets()
        return self 

    def get_search_tweets(self):
        """Find tweets matching keywords"""
        match_tweet(self.tweetCurs, self.keywords, 'tdate')
        self.add_filtered_results()
        self.more_results()

    def get_user_tweets(self):
        """Find tweets/retweets from users who are being followed"""
        follows_tweets(self.tweetCurs, self.user)
        self.add_results()
        self.more_results()

    def add_results(self):
        """Adds tweets from the query resuls into the all_tweets list"""
        for row in self.tweetCurs.fetchall():
            tweet = Tweet(self.session, row)
            self.all_tweets.append(tweet)

    def add_filtered_results(self):
        """Remove tweets from all_tweets list if the tweet does not match
        a keyword
        """
        for row in self.tweetCurs.fetchall():
            tweet = Tweet(self.session, data=row)
            valid_tweet = True
            if len(self.keywords) > 0:
                valid_tweet = self.validate_tweet(tweet)

            if valid_tweet:
                self.all_tweets.append(tweet)

    def validate_tweet(self, tweet):
        """Returns true if a keyword is not a hashtag and the tweet does not mention it

        :param tweet: Tweet object
        """
        terms = tweet.get_terms()
        for word in self.keywords:
            if is_hashtag(word) and word.replace('#', '') in terms:
               return True
            elif not is_hashtag(word) and word in tweet.get_nohash():
               return True 
        return False 

    def more_results(self):
        """Gets the next 5 tweets from users who are being followed"""
        assert(self.tweetCurs is not None), 'Unable to select more tweets'

        self.tweets = self.all_tweets[self.tweet_index - 5:self.tweet_index]
        self.more_exist = len(self.all_tweets) - self.tweet_index > 0
        self.tweet_index += 5
  
    def display_results(self):
        """Display resulting tweets 5 at a time ordered by date"""
        print_border(thick=True) 
        if self.search: 
            title = "SEARCH RESULTS FOR %s" % (self.get_searched().upper())
            print_string(title)
        else: 
            title = "HOME"
            split_title(title, self.session.get_name().upper())
        print_border(thick=True, sign='|') 

        if self.search:
            result = "Result"
            width = 65
        else:        
            result = ""
            width = 70

        for i, tweet in enumerate(self.tweets):
            rt_user = tweet.retweeter()
            if rt_user and tweet.author() != rt_user: 
                tweet.display(index=i, rt_user=rt_user, result=result, width=width)
            else:
                tweet.display(index=i, result=result, width=width)

            if i == len(self.tweets) - 1:
                print_border(thick=False, sign='+')
            else:
                print_border(thick=False, sign='|')

        if len(self.tweets) == 0:
            if self.search: 
                print_string("Sorry, there are no tweets that match that query.")
            else:
                print_string("You are not following anyone.")
            print_border(thick=False, sign='|')

    def select_result(self, tweet):
        """Prompt user to choose one of the displayed tweets
        
        param tweet: The tweet that the user selected 
        """
        option = tweet.display_stats()

        if option == "Reply":
            tweet.reply()
            self.select_result(tweet)
        elif option == "Retweet":
            tweet.retweet()         
            self.select_result(tweet)                
        elif option == "Go back":
            self.session.home(self, reset=False) 
        elif option == "Search for other tweets":
            new_search = search_tweets(self.session)
            self.session.home(new_search, reset=False)
        elif option == "Home":
            self.session.home()
        elif option == "Logout":
            self.session.logout()

        self.session.home(self)
            
    def choose_result(self):
        """Returns the number of the tweet the user wants to select"""
        prompt = "Enter the result number to select: "
        choice = validate_num(prompt, self.session, size=len(self.tweets))
        if check_quit(choice):
            self.session.home(self)
        else:
            choice -= 1

        tweet = self.tweets[choice]
        self.select_result(tweet)

    def results_exist(self):
        """Return true if user has tweets to display"""
        return True if len(self.tweets) > 0 else False

    def more_results_exist(self):
        """Return true if more tweets can be displayed"""
        return self.more_exist
