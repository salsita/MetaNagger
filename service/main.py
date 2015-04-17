""" This is a service intended to be run periodically as a CRON job.

    It randomly selects a RB review that got ship-it label in last 5 days and
    notifies configured user about hte review on slack.

    The service expects a '${HOME}/.workflow.cfg' file with the following structure:

    [auth]
    rb_user = <reviewboard username>
    rb_pwd = <password for the reviewboard user>
    slack_token = <slack token, apparently>

    The users (in PT & RB) should have access to all the projects (otherwise the
    service will not be able to update all the stories).
"""

import os
import rb.extensions
import ConfigParser
import datetime
import random

from slacker import Slacker
from dateutil.relativedelta import relativedelta as delta

CFG_FILE = '%s/.workflow.cfg' % os.environ['HOME']

DAYS_DELTA = 5  # how old can the reviews be?
METAREVIEWER_SLACK_NAME = 'matt'
REVIEW_URL_ROOT = 'https://review.salsitasoft.com/r/'


# Get RB reviews (ship-it'ed in last 5 days) with provided status
def get_reviews(status, auth):
    time_added = datetime.date.today() - delta(days=5)
    return rb.extensions.get_review_requests2({
        'max-results': 200,
        'ship-it-count-gt': 0,
        'last-updated-from': time_added,
        'status': status
    }, auth)

# Parse review requests, group their respective ids by repository name
def group_ids_by_rep_name(reviews, result):
    for r in reviews:
        rep_name = r['links']['repository']['title']
        result[rep_name] = result.get(rep_name, []);
        result[rep_name].append(r['id'])

# Notify user on slack
def notify(slack_token, message):
    slack = Slacker(slack_token)
    try:
        slack.chat.post_message('@' + METAREVIEWER_SLACK_NAME, message)
    except Exception, e:
        print '>>> ERROR when notifying user', e

def main():
    # Read the sensitive data from a config file
    config = ConfigParser.RawConfigParser()
    config.read(CFG_FILE)
    rb_user = config.get('auth', 'rb_user')
    rb_pwd = config.get('auth', 'rb_pwd')
    slack_token = config.get('auth', 'slack_token')

    # Get requests (status: pending, submitted)
    auth = {'username': rb_user, 'password': rb_pwd}
    reqs_pending = get_reviews('pending', auth)
    reqs_submitted = get_reviews('submitted', auth)

    # Group request ids by repository name
    reqs = {}
    group_ids_by_rep_name(reqs_pending, reqs)
    group_ids_by_rep_name(reqs_submitted, reqs)
   
    # Pick one review and let metareviewer know about it
    if len(reqs) is 0:
        notify(
            slack_token,
            'No metareview for today, it seems there was no ship-it-ed review in last 5 days! :wonder:'
        )
        return
    repo = random.choice(reqs.keys())
    req = random.choice(reqs[repo])
    comment = '' 
    total = 0
    for r in reqs.keys():
        cnt = len(reqs[r])
        comment = comment + ('\n+ %s %s from project %s' % 
            (cnt, 'review' if cnt == 1 else 'reviews', r))
        total = total + cnt
    comment = ('\nThe review was randomly (but carefully) chosen from %s %s:' % 
        (total, 'review' if total == 1 else 'reviews')) + comment
    notify(
        slack_token,
        (('Your lucky metareview URL for today is: %s%s\n' +
         'Project: %s\n') % (REVIEW_URL_ROOT, req, repo)) + comment
    )

if __name__ == '__main__':
    main()
