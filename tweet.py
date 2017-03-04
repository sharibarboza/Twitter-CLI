from constants import SELECT, TODAY

from utils import (
    convert_date, 
    display_selections, 
    validate_num,
    validate_yn,
    press_enter
)

from queries import (
    select,
    follows_tweets,
    get_name,
    get_user_from_tid,
    get_text_from_tid,
    get_rep_cnt,
    get_ret_cnt,
    insert_retweet,
    insert_tweet,
    already_retweeted,
    tid_exists
)

def compose_tweet(conn, user, replyto=None):
    """
    Generates a new tweet
    """
    text = input("Enter tweet: ")
    writer = user
    tid = generate_tid(conn)
    date = TODAY
    replyto = replyto
    rt_user = None
    data = [tid, writer, date, text, replyto, rt_user]
    new_tweet = Tweet(conn, user, data)
    new_tweet.display()

    confirm = validate_yn("Confirm tweet? y/n: ")
    if confirm in ["n", "no"]:
        print("Tweet cancelled.")
    else:
        insert_tweet(conn, new_tweet.get_values())
        print("Tweet %d created." % (new_tweet.id))


def generate_tid(conn):
    """
    Generates a new unique tweet id
    """
    curs = conn.cursor()
    select(curs, 'tweets')
    rows = curs.fetchall()
    new_tid = len(rows) + 1
    
    while tid_exists(curs, new_tid): 
        new_tid += 1
    
    curs.close()
    return new_tid

class Tweet:

    def __init__(self, conn, user, data):
        self.conn = conn
        self.curs = conn.cursor()
        self.user = user

        # Tweet database values
        self.id = data[0]
        self.writer = data[1]
        self.date = data[2]
        self.text = data[3]
        self.replyto = data[4]
        self.rt_user = data[5]

        if self.replyto:
            self.reply_user = get_user_from_tid(self.curs, self.replyto)
            self.reply_name = get_name(self.curs, self.reply_user)
            self.reply_text = get_text_from_tid(self.curs, self.replyto)

        if self.rt_user:
            self.rt_name = get_name(self.curs, self.rt_user)

        self.date_str = convert_date(self.date)
        self.rep_cnt = get_rep_cnt(self.curs, self.id)
        self.ret_cnt = get_ret_cnt(self.curs, self.id)
        self.writer_name = get_name(self.curs, self.writer)

    def display(self, user=None):
        if self.is_retweet(): 
            print("%s Retweeted" % (self.rt_name))         
        elif user:
            user_name = get_name(self.curs, user)
            print("%s Retweeted" % (user_name))

        print("%s @%d - %s" % (self.writer_name, self.writer, self.date_str))
        print("%s\n" % (self.text))

    def display_stats(self):
        print("\nTWEET STATISTICS\n")
        print("Tweet id: %d" % (self.id))
        print("Written by: %s @%d" % (self.writer_name, self.writer))
        print("Posted: %s" % (self.date_str))
        print("Text: %s" % (self.text))

        if (self.replyto):
            print("Reply to: %s (%s @%d)" % (self.reply_text, self.reply_name, self.reply_user))
        else:
            print("Reply to: None")

        print("Number of replies: %s" % (self.rep_cnt))
        print("Number of retweets: %s" % (self.ret_cnt))

    def tweet_menu(self):
        choices = ["Reply", "Retweet", "Home", "Logout"]
        display_selections(choices)
        choice = validate_num(SELECT, size=len(choices))

        if choice == 1:
            compose_tweet(self.conn, self.user)
        elif choice == 2:
            self.retweet()
        elif choice == 4:
            choice = 6
        return choice

    def retweet(self):
        if already_retweeted(self.curs, self.user, self.id):
            print("You already retweeted this tweet.")
            return
            
        self.display(self.user)

        confirm = validate_yn("Confirm retweet? y/n: ")
        if confirm in ["n", "no"]:
            print("Retweet cancelled.")
        else:
            print("Retweeted - %s" % (TODAY))
            data_list = [user, self.id, TODAY]
            insert_retweet(self.conn, data_list)

    def is_retweet(self):
        return self.rt_user is not None and self.writer != self.rt_user

    def get_values(self):
        return [self.id, self.writer, self.date, self.text, self.replyto]


class TweetSearch:

    def __init__(self, conn, user):
        self.conn = conn
        self.user = user
        self.tweets = []

    def get_user_tweets(self):
        curs = self.conn.cursor()
        follows_tweets(curs, self.user)

        self.rows = curs.fetchmany(5)
        self.display_tweets()
       
        if len(self.rows) > 0:
            return curs
        else:
            curs.close()
            return None 

    def display_tweets(self):
        for i, row in enumerate(self.rows, 1):
            print("Tweet %d" % (i))
            tweet = Tweet(self.conn, self.user, data=row)
            self.tweets.append(tweet)
            tweet.display()

        if len(self.rows) == 0:
            print("You have no tweets yet.")

    def select_tweet(self):
        tweet_num = self.choose_tweet()
        tweet = self.tweets[tweet_num - 1]
        tweet.display_stats()

        choice = 0
        while choice < 3:
            choice = tweet.tweet_menu()

        return choice

    def choose_tweet(self):
        choices = []
        for i, row in enumerate(self.rows, 1):
            tweet_str = "Tweet %d" % (i)
            choices.append(tweet_str)

        display_selections(choices)
        return validate_num(SELECT, size=len(choices))

