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
import humanize

import pytz
import datetime
import dateutil.parser


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


    def _get_djs(self, show):
        djs = []
        for dj in show['dj']:
            djs.append(dj['dj_name'])
        return djs


    def _format_time(self, time_string):
        return humanize.time.naturaldelta(pytz.utc.localize(datetime.datetime.utcnow()) - dateutil.parser.parse(time_string))


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

    dj = wrap(dj)


    def kickdj(self, irc, msg, args):
        """
        Kick the currently streaming dj
        """

        try:
            kick_dj = self._query('kick_dj')['data']['kick_dj']

            if kick_dj:
                reply = u'%s was kicked successfully' % kick_dj['dj_name']
            else:
                reply = u'Cleansing could not be completed'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    kickdj = wrap(kickdj, ['admin'])


    def track(self, irc, msg, args):
        """
        Return the currently playing track
        """

        try:
            current_track = self._query('current_track')['data']['current_track']

            if current_track:
                reply = u'%s - %s' % (current_track['track_artist'], current_track['track_title'])
            else:
                reply = u'Nothing is on right now'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    track = wrap(track)


    def tracklist(self, irc, msg, args, num=3):
        """
        Return the last x played tracks (default: x = 3)
        """

        try:
            last_tracks = self._query('last_tracks')['data']['last_tracks']

            if last_tracks:

                reply_tracks = []
                for track in last_tracks['tracks']:
                    reply_tracks.append('[%s - %s]' % (track['track_artist'], track['track_title']))
                reply = u', '.join(reply_tracks)

            else:
                reply = u'Track history is empty'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    tracklist = wrap(tracklist, [optional('int')])


    def listener(self, irc, msg, args):
        """
        Return the current listener count and additional stats
        """

        try:
            listener = self._query('listener')['data']['listener']

            if listener:

                if listener['total_count'] > 0:

                    reply_stream = []
                    streams = sorted(listener['per_stream'].iteritems(), key=operator.itemgetter(1), reverse=True)
                    for stream in streams:
                        reply_stream.append('%d via %s' % (stream[1]['count'], stream[1]['name']))
                    reply_stream = ' | '.join(reply_stream)

                    foreigner_count = 0
                    reply_country = []
                    countries = sorted(listener['per_country'].iteritems(), key=operator.itemgetter(1), reverse=True)
                    for country in countries:
                        reply_country.append('%s: %d' % (country[0], country[1]['count']))
                        if country[0] not in ('DE', 'BAY'):
                            foreigner_count += country[1]['count']
                    reply_country = ' | '.join(reply_country)
                    foreigner_count = int((float(foreigner_count) / float(total_count)) * 100)

                    reply = u'Listener: %d ( %s )( %s )( %d%% foreigners )' % (listener['total_count'], reply_stream, reply_country, foreigner_count)

                else:
                    reply = u'No one is listening right now'

        except:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    listener = wrap(listener)


    def show(self, irc, msg, args):
        """
        Return information about the current show
        """

        try:
            current_show = self._query('current_show')['data']['current_show']

            if current_show:

                # overlap dedection
                if 'planned_show' in current_show:
                    # we got ourselves a overlap
                    # planned_show <- what should be running
                    # running_show <- what is running at the moment
                    planned_show = current_show['planned_show']
                    running_show = current_show['running_show']

                    reply = u'%s with %s is supposed to run but %s with %s is on instead' % (
                        planned_show['show_name'], ' and '.join(self._get_djs(planned_show)),
                        running_show['show_name'], ' and '.join(self._get_djs(running_show)))

                else:
                    running_show = current_show['running_show']

                    # check if one the djs is really connected
                    if running_show['show_connected'] == True:
                        reply = u'%s (%s) with %s is on right now, %s to go' % (
                            running_show['show_name'], running_show['show_description'], ' and '.join(self._get_djs(running_show)), self._format_time(running_show['show_end']))

                    else:
                        reply = u'%s with %s is supposed to run for %s but no one is streaming right now' % (
                            running_show['show_name'], ' and '.join(self._get_djs(running_show)), self._format_time(running_show['show_begin']))

            else:
                reply = u'No one is streaming right now'

        except Exception, e:
            reply = self.reply_error

        finally:
            irc.reply(reply)

    show = wrap(show)


Class = RfK


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
