###
# Copyright (c) 2013, MrLoom
# All rights reserved.
#
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.schedule as schedule
import supybot.ircmsgs as ircmsgs

import supybot.log as log

import json
import urllib
import urllib2

import operator


class RfK(callbacks.Plugin):
    """RfK MK IV supybot plugin"""

    threaded = True

    def __init__(self, irc):
        self.__parent = super(RfK, self)
        self.__parent.__init__(irc)

        self.last_track_id = None
        self.last_dj_id = None
        self.last_dj_name = None

        self.reply_error = u'Sorry, an error occurred'

        def poll_event():
            try:

                # check for dj changes
                result = self._query('current_dj')
                current_dj = result['data']['current_dj']

                # dj stopped streaming
                if not current_dj and self.last_dj_id:
                    announce = u'%s stopped streaming' % self.last_dj_name
                    self._announce(irc, announce)

                # dj started streaming
                elif current_dj and not self.last_dj_id:
                    announce = u'%s started streaming' % current_dj['dj_name']
                    self._announce(irc, announce)

                # dj changed since last check
                elif current_dj and self.last_dj_id and current_dj['dj_id'] != self.last_dj_id:
                    announce = u'Instead of %s, %s is streaming now' % (self.last_dj_name, current_dj['dj_name'])
                    self._announce(irc, announce)

                self.last_dj_id = current_dj['dj_id'] if current_dj else None
                self.last_dj_name = current_dj['dj_name'] if current_dj else None

                # check for track changes
                result = self._query('current_track')
                current_track = result['data']['current_track']

                if current_track and self.last_track_id != current_track['track_id']:
                    announce = u'%s - %s' % (current_track['track_artist'], current_track['track_title'])
                    self._announce(irc, announce)

                self.last_track_id = current_track['track_id'] if current_track else None

            except Exception, e:
                log.error('RfK.poll_event: %s' % repr(e))

        # remove any old events
        if 'RfK.pollStatus' in schedule.schedule.events:
            schedule.removePeriodicEvent('RfK.pollStatus')

        # register event
        if self.registryValue('enablePolling'):
            schedule.addPeriodicEvent(poll_event,
                self.registryValue('pollingInterval'),
                name='RfK.pollStatus')


    def _query(self, function, **params):
        log.debug('RfK._query: %s' % repr(params))

        if self.registryValue('httpProxy'):
            opener = urllib2.build_opener(
                urllib2.ProxyHandler({'http': self.registryValue('httpProxy')}))
        else:
            opener = urllib2.build_opener()

        request_url = '%s%s?key=%s&%s' % (self.registryValue('queryURL'), function,
            self.registryValue('queryPass'), urllib.urlencode(params))

        try:
            response = opener.open(request_url)
        except IOError, e:
            log.error('RfK._query: %s' % repr(e))
        else:
            try:
                data = json.loads(response.read())
            except ValueError, e:
                log.error('RfK._query: %s' % repr(e))
            else:
                if data['status']['code'] != 0:
                    log.error('RfK._query: %s' % repr(data))
                else:
                    log.debug('RfK._query: %s' % repr(data))
                    return data
                    

    def _announce(self, irc, message):
        message = u'%s %s' % (self.registryValue('announcePrefix'), message)
        for channel in irc.state.channels:
            if self.registryValue('announce', channel):
                irc.queueMsg(ircmsgs.privmsg(channel, message))


    def dj(self, irc, msg, args):
        """
        Return the currently streaming dj
        """

        try:
            current_dj = self._query('current_dj')['data']['current_dj']
            if current_dj:
                reply = u'%s is streaming right now' % current_dj['dj_name']
            else:
                reply = u'No one is streaming right now'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    def listener(self, irc, msg, args):
        """
        Return the corrent listener count and additional stats
        """

        try:
            listener = self._query('listener')['data']['listener']
            if listener:

                if listener['total_count'] > 0:

                    reply_stream = []
                    streams = sorted(listener['per_stream'].iteritems(), key=operator.itemgetter(1), reverse=True)
                    for stream in streams:
                        reply_stream.append('%d via %s' % (stream[1]['count'], stream[1]['name']))
                    reply_stream = '%s' % (' | '.join(reply_stream))

                    foreigner_count = 0
                    reply_country = []
                    countries = sorted(listener['per_country'].iteritems(), key=operator.itemgetter(1), reverse=True)
                    for country in countries:
                        reply_country.append('%s: %d' % (country[0], country[1]['count']))
                        if country[0] not in ('DE', 'BAY'):
                            foreigner_count += country[1]['count']
                    reply_country = '%s' % (' | '.join(reply_country))
                    foreigner_count = int((float(foreigner_count) / float(total_count)) * 100)

                    reply = 'Listener: %d ( %s )( %s )( %d%% foreigners' % (listener['total_count'], reply_stream, reply_country, foreigner_count)

                else:
                    reply = 'No one is listening right now'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)


Class = RfK


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
