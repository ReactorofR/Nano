import discord
import asyncio
import random
import re
import os
import sys
import django
import datetime

qtpath = r"E:\Projects\Discord bot\QTBOT\qtbot"
sys.path.append(qtpath)

os.environ["DJANGO_SETTINGS_MODULE"] = "qtbot.settings"
django.setup()
from girldatabase.models import QtAnimeGirl, Tag
from django.db.models import Max, Min

image_directory = r"E:\Projects\Discord bot\QTBOT\qtbot\girldatabase\images"
# Should probably be reading this from a file somewhere.
# Maybe make a config file?
owner_id = discord.User(id='191275079433322496')

client = discord.Client()
battles_ongoing = {}

class qt_battle():
    def __init__(self):
        self.girls = [QtAnimeGirl(), QtAnimeGirl()]
        self.caller = discord.User()
        self.vote = discord.Message()
        # TODO: These should REALLY be attributes of a QtAnimeGirl
        self.vote_A = 0
        self.vote_B = 0
        self.voters = {}
        self.is_ongoing = True
        self.time_start = datetime.datetime.now()
    def name(self, girl, new_name):
        # 'girl' should be either 1 or 2.
        # I've done some ripping here so it might be buggy, beware.
        self.girls[girl - 1].name = new_name
        self.girls[girl - 1].save()
    def vote_girl(self, girl, author):
        letter = 'A' if girl == 1 else 'B'
        if author in self.voters:
            # I don't know why we're using 'is' here instead of '=='.
            # I'm leaving it like this, because else it might break.
            if self.voters[author] is 2:
                self.vote_B -= 1
            else:
                self.vote_A -= 1
        setattr(self, "vote_{0}".format(letter), 1)
        self.voters[author] = girl
    def drop(self, girl):
        self.girls[girl].delete()
    def tag(self, girl, message):
        # TODO: Comment this hideous regex.
        # Probably rewrite it too.
        tag_search = re.compile('(((?<=>tag\s{}\s)([a-zA-Z0-9-0_]+))|((?<=,)([a-zA-Z0-9-0_]+))|((?<=,\s)([a-zA-Z0-9-0_]+)))'.format(girl))
        tags = re.finditer(tag_search, message)
        tag_list = []
        for tag in tags:
            self.girls[girl-1].addTag(tag.group())
            tag_list.append(tag.group())
        return ', '.join(tag_list)
    def tags(self, girl):
        tag_objects = self.girls[girl-1].tags.all()
        tags = []
        for x in tag_objects:
            tags.append(x.tag)
        return ', '.join(tags)
    def end(self):
        draw = (self.vote_A == self.vote_B)
        if not draw:
            winner = 1 if max(self.vote_A, self.vote_B) == self.vote_A else 2
            # Relies on the fact that 3 - 2 = 1 and 3 - 1 = 2.
            loser = 3 - winner
            oldELO = self.girls[winner - 1].elo
            self.girls[winner - 1].updateELO(self.girls[loser - 1].elo, 1)
            self.girls[loser - 1].updateELO(self.girls[winner - 1].elo, 0)
            return '{0} Wins! Her rating is now {1}(+{2})'.format(self.girls[winner - 1],
                                                                  self.girls[winner - 1].elo,
                                                                  self.girls[winner - 1].elo - oldELO)
        else:
            old_ELO_A = self.girls[0].elo
            old_ELO_B = self.girls[1].elo
            self.girls[0].updateELO(self.girls[1].elo, 0.5)
            self.girls[1].updateELO(self.girls[0].elo, 0.5)
            return "It's a tie! QTR change: {} ({})  {} ({})".format(self.girls[0],
                                                                     self.girls[0].elo - old_ELO_A,
                                                                     self.girls[1],
                                                                     self.girls[1].elo - old_ELO_B)

@client.event
async def on_ready():
    print('''Logged in as\n{0}\n{1}\n------
        '''.format(client.user.name, client.user.id))

@client.event
async def on_message(message):
    if(message.content.startswith('>qtbattle')
       or message.content.startswith('>qtb')
       and not message.channel in battles_ongoing):
        all_girls = []
        battle = qt_battle()
        battles_ongoing[message.channel] = battle
        print('Starting QT battle')

        battle.caller = message.author
        tag_regex = re.compile(r'((((?<=>qtb\s)|(?<=>qtbattle\s))([a-zA-Z0-9-0_]+))|((?<=,)([a-zA-Z0-9-0_]+)))')
        tags = re.finditer(tag_regex, message.content)

        if message.content == ('>qtb') or message.content == ('>qtbattle'):
            all_girls = QtAnimeGirl.objects.all()
        else:
            for x in tags:
                try:
                    tag_object = Tag.objects.get(tag=x.group)
                    girls_with_tag = tag_object.qtanimegirl_set.all()
                    for x in girls_with_tag:
                        if x.id not in all_girls:
                            all_girls.append(x.id)
                # Smith: This error has a weird name - did you write that error in the other file?
                # Error names should end in -Error.
                except Tag.DoesNotExist:
                    pass
            if len(all_girls) >= 2:
                all_girls = QtAnimeGirl.objects.filter(id__in=all_girls)
            else:
                tmp = await client.send_message(message.channel,
                                                "Couldn't find enough girls with provided tags, using random girls")
                all_girls = QtAnimeGirl.objects.all()

        battle.girls = random.sample(list(all_girls), 2)

        print('Girl 1 = {}({})'.format(battle.girls[0].id, battle.girls[0].elo))
        print('Girl 2 = {}({})'.format(battle.girls[1].id, battle.girls[1].elo))
        print('--------------')

        await client.send_typing(message.channel)
        await client.send_file(message.channel,
                               open(os.path.join(image_directory, battle.girls[0].image), 'rb'),
                               filename=battle.girls[0].image,
                               content='{0} with a {1} ranking'.format(battle.girls[0], battle.girls[0].elo))
        await client.send_typing(message.channel)
        await client.send_file(message.channel,
                               open(os.path.join(image_directory, battle.girls[1].image), 'rb'),
                               filename=battle.girls[1].image,
                               content='{0} with a {1} ranking'.format(battle.girls[1], battle.girls[1].elo))
        try:
            await client.delete_message(tmp)
        # FIXME: Bare exception - what exception does this throw?
        except:
            pass

        battle.vote = await client.send_message(message.channel,
                                                '%s vs %s - 0 - 0' % (battle.girls[0], battle.girls[1]))
        battle.time_start = datetime.datetime.now()
        battles_ongoing[message.channel] = battle

    elif (message.content.startswith('>qtbattle')
          or message.content.startswith('>qtb')
          and message.channel in battles_ongoing):
        await client.send_message(message.channel, 'Only 1 ongoing battle per channel!')

    if message.channel in battles_ongoing:
        battle = battles_ongoing[message.channel]

        if message.content.startswith('>name'):
            girl = int(message.content[6])
            new_name = re.search(r'(?<=\>name\s{0}\s).+'.format(girl), message.content).group()
            battle.name(girl, new_name)
            await client.send_message(message.channel,
                                      'Girl {0} now known as {1}!'.format(battle.girls[girl - 1].id,
                                                                          battle.girls[girl - 1]))
        message.content = message.content.lower()
        if message.content.startswith('>vote'):
            if message.content[6] == 1 or message.content[6] == 2:
                girl = int(message.content[6])
                battle.vote_girl(girl, message.author)
                # TODO: This is ugly. Maybe votes should be a property of QtAnimeGirl objects? I can't edit that code right now though.
                await client.edit_message(battle.vote,'%s vs %s - %s - %s' % (battle.girls[0],battle.girls[1],battle.vote_A,battle.vote_B))
        elif (message.content.startswith('>drop') and (message.author == owner_id)):
            girl = int(message.content[6])
            battle.drop(girl)
            await client.send_message(message.channel,
                                      'Girl {} has been dropped from the database!'.format(battle.girls[girl - 1]))
        elif message.content.startswith('>tag '):
            # Space after '>tag' otherwise '>tags' would also pass
            girl = int(message.content[5])
            await client.delete_message(message)
            s = battle.tag(girl, message.content)
            await client.send_message(message.channel, 'Tags {} added to {}'.format(s, battle.girls[girl - 1]))
        elif message.content.startswith('>tags'):
            girl = int(message.content[6])
            await client.delete_message(message)
            tags = battle.tags(girl)
            await client.send_message(message.channel, "{}'s tags: {}".format(battle.girls[girl - 1], tags))
        elif (message.content.startswith('>end')
              and ((message.author == battle.caller) or (message.author == owner_id))):
            battle.is_ongoing = False

        timedelta = datetime.datetime.now() - battle.time_start
        if timedelta.seconds > 180 or not battle.is_ongoing:
            del battles_ongoing[message.channel]
            end_message = battle.end()
            await client.send_message(message.channel, end_message)

    # This part is unbelievably bad, but I don't see an easy fix right now.
    # TODO: Rewrite all of this.
    if message.content.startswith('>bestgirl'):
        elo = QtAnimeGirl.objects.aggregate(Max('elo'))
        # What's the idea with the double underscores (elo__max)?
        bestgirl = QtAnimeGirl.objects.filter(elo=elo['elo__max'])
        if len(bestgirl) > 1:
            await client.send_message(message.channel, "It's a tie between {} girls!".format(len(bestgirl)))
            for x in bestgirl:
                await client.send_typing(message.channel)
                await client.send_file(
                    message.channel,
                    open(os.path.join(image_directory, x.image), 'rb'),
                    filename=x.image,
                    content='{0} with a {1} ranking'.format(x, x.elo))
        else:
            await client.send_message(message.channel, "Best girl!")
            await client.send_file(
                message.channel,
                open(os.path.join(image_directory, bestgirl[0].image), 'rb'),
                filename=bestgirl[0].image,
                content='{0} with a {1} ranking'.format(bestgirl[0], bestgirl[0].elo))

    elif message.content.startswith('>worstgirl'):
        elo = QtAnimeGirl.objects.aggregate(Min('elo'))
        worstgirl = QtAnimeGirl.objects.filter(elo=elo['elo__min'])
        if len(worstgirl) > 1:
            await client.send_message(message.channel, "It's a tie between {} girls!".format(len(worstgirl)))
            for x in worstgirl:
                await client.send_typing(message.channel)
                await client.send_file(
                    message.channel,
                    open(os.path.join(image_directory, x.image), 'rb'),
                    filename=x.image,
                    content='{0} with a {1} ranking'.format(x, x.elo))
        else:
            await client.send_message(message.channel, "Worst girl!")
            await client.send_file(
                message.channel,
                open(os.path.join(image_directory, worstgirl[0].image), 'rb'),
                filename=worstgirl[0].image,
                content='{0} with a {1} ranking'.format(worstgirl[0], worstgirl[0].elo))

    elif message.content.startswith('>updategirls') and message.author == owner_id:
        anime_girl = QtAnimeGirl()
        new_girls = anime_girl.getNewGirls(image_directory)
        await client.send_message(message.channel, "{} new girls added!".format(new_girls))

    elif message.content.startswith('-randqt'):
        tag_regex = re.compile(r'(((?<=-randqt\s)([a-zA-Z0-9-0_]+))|((?<=,)([a-zA-Z0-9-0_]+)))')
        # FIXME: Redefinition from str to list.
        tags = list(re.finditer(tag_regex, message.content))
        all_girls = []
        info = ''
        if message.content == ('-randqt'):
            all_girls = QtAnimeGirl.objects.all()
        else:
            query = QtAnimeGirl.objects
            for x in tags:
                query = query.filter(tags__tag=x.group())
            try:
                all_girls = query
            # FIXME: Bare except
            except:
                pass
            if not all_girls:
                #using filter() made all_girls a QuerySet object
                all_girls = []
                for x in tags:
                    try:
                        girls_with_tag = QtAnimeGirl.objects.filter(tags__tag=x.group())
                        for z in girls_with_tag:
                            if z not in all_girls:
                                all_girls.append(z)
                    except Tag.DoesNotExist:
                        pass
        if not all_girls:
            all_girls = QtAnimeGirl.objects.all()
            info = 'No girls found with tags provided'
        girl = random.choice(all_girls)
        #If girl found with provided tags list them
        if not info:
            # FIXME: This will crash if the previous condition (not all_girls) does not evaluate to True
            # In that case, girl will be an int, which has no attribute 'tags'
            # I'm not sure if this can ever occur.
            # This variable should probably be named differently regardless,
            # as it's easy to mistake this for the int with the same name.
            tag_objects = girl.tags.all()
            tags = []
            for x in tag_objects:
                tags.append(x.tag)
            info = ', '.join(tags)

        await client.send_typing(message.channel)
        qt = await client.send_file(
            message.channel,
            open(os.path.join(image_directory, girl.image), 'rb'),
            filename=girl.image,
            content='Random QT! {} [{}]'.format(girl, info))
        await asyncio.sleep(60)
        await client.delete_message(message)
        await client.delete_message(qt)

    # This should probably not be in the qtbattle file :-).
    elif message.content.startswith('-rand'):
        search_param = re.search(r'(?<=-rand\s)[0-9]+', message.content)
        try:
            param = int(search_param.group())
            mention = message.author.mention
            await client.send_message(message.channel,
                                      '{} rolled **{}**'.format(mention, random.randint(0, param)))
        # FIXME: Bare except
        except:
            pass

    elif message.content.startswith('>setgame') and (message.author == owner_id):
        search_param = re.search(r'(?<=\>setgame\s).+', message.content)
        game = discord.Game(name=search_param.group())
        await client.change_status(game)

    elif message.content.startswith('>help'):
        await client.send_message(
            message.channel,
            '''
           ```Hakase commands:
           ---------
           >qtbattle tags*------Start qt battle (*optional, seperated by commas)
           -rand argument ------Random number
           -randqt tags* -------Random qt (*optional, seperated by commas)
           >bestgirl -----------Shows girl or girls with the highest rating
           >worstgirl ----------Shows girl or girls with the lowest rating

           While in QTBattle:
           ---------
           >vote 1/2 -----------Vote for girl
           >tag 1/2 tag1,tag2 --Tag girl
           >tags 1/2 -----------See girls tags
           >name 1/2 name ------Gives girl a name
           >end ----------------Ends QTBattle(user who started it only)
           ```
           ''')

    elif message.content.startswith('-denko'):
        await client.delete_message(message)
        await client.send_message(message.channel, '(´・ω・`)')

    if ':B1:' in message.content:
        await client.send_file(message.channel, open(r'misc files\B1.png', 'rb'), filename=r'B1.png')
    if ':B2:' in message.content:
        await client.send_file(message.channel, open(r'misc files\B2.png', 'rb'), filename=r'B2.png')
    if ':sectoid:' in message.content:
        await client.send_file(message.channel, open(r'misc files\-sectoid-.png', 'rb'), filename=r'-sectoid-.png')

if __name__ == "__main__":
    client.run('MjAwMjgzMTI0NjE2MTM0NjU3.CmAOIA.Eg7---YpjaI5Hto3tyH3UH2jjhI')
