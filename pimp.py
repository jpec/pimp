#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PiMP, the PI Media Player.

PiMP is a simple media player designed for the Raspberry Pi. 
It works in console mode and use OMXPLAYER backend for hardware video 
acceleration. Since the 0.6 version, it's possible to choose another
backend.

Author:  Julien Pecqueur
Email:   julien@peclu.net
Home:    http://peclu.net/~pimp
Sources: https://github.com/jpec/pimp

This software is provided without any warranty. 

If you want to improve it, modify it, correct it, please send me your 
modifications so i'll backport them on the reference tree.

Have fun.

Julien

"""
VERSION = 0.8

# Allowed movies extensions
EXTENSIONS = ["avi", "mpg", "mp4", "mkv"]

# Keys definition
K_NEXT="k"
K_PREV="i"
K_NPAG="h"
K_PPAG="y"
K_PLAY="p"
K_SCAN="R"
K_QUIT="Q"
K_FIND="f"


import curses
import sys
import os
import subprocess


def compute_args(args):
    "Compute command line"
    cmd = ""
    if len(args) == 1:
        return("")
    for a in args[1:]:
        a = a.strip()
        if a == '':
            continue
        cmd = cmd + a + " "
    return(cmd)


def get_subtitle_if_exists(movie):
    "Get subtitle file"
    sub = movie[0:-3] + "srt"
    if os.path.isfile(sub):
        return('--subtitles \"{0}\"'.format(sub))
    return("")


def play(movie, player="omxplayer", args=[]):
    "Play a movie"
    if player == "omxplayer":
        sub = get_subtitle_if_exists(movie)
        if sub != "":
    	    args.append(sub)
    options = compute_args(args)
    if len(options) >1:
        cmd = '{0} {1}\"{2}\"'.format(player, options, movie)
    else:
        cmd = '{0} \"{1}\"'.format(player, movie)
    r = subprocess.call(cmd + ' > /dev/null', shell=True)
    return(cmd)


def scan_dir_movies_for_movies(dir_movies):
    "Scan dir_movies directory for movies and return a list."
    lst_movies = list()
    for f in os.listdir(dir_movies):
        p = dir_movies+"/"+f
        if f[0] == ".":
            continue
        elif os.path.isdir(p):
            lst_movies += scan_dir_movies_for_movies(p)
        elif os.path.isfile(p) and f[-3:] in EXTENSIONS:
            lst_movies.append(p)
    return(lst_movies)


def get_movies_from_dir_movies(dir_movies):
    "Get movies from dimovier_movies directories and return a dictionary."
    dic_movies = dict()
    for d in dir_movies:
        if os.path.isdir(d):
            lst_paths = scan_dir_movies_for_movies(d)
            if not lst_paths:
                continue
            for p in lst_paths:
                dic_movies[os.path.basename(p)] = p
    return(dic_movies)


def get_movies_from_db(db):
    "Read db and return a dictionary."
    if os.path.isfile(db):
        f = open(db, "r")
        dic_movies = dict()
        for l in f.readlines():
            l = l.replace("\n", "")
            dic_movies[os.path.basename(l)] = l
        f.close()
        return(dic_movies)
    else:
        return(None)


def save_movies_to_db(db, dic_movies):
    "Save movies to db."
    f = open(db, "w")
    for e in dic_movies:
        f.write(dic_movies[e]+"\n")
    f.close()
    return(True)


def parse_args(test=False):
    "Parse command line parameters."
    dir_movies = list()
    omx_args = list()
    player = "omxplayer"
    for a in sys.argv:
        if (a == "-h" or a == "--help") and test:
            print("Usage: pimp [options]")
            print("Options:")
            print("--player=<player executable> to specify a player")
            print("any directories containing movies")
            print("omxplayers's options for the default player")
            return(False)
        if len(a) > 9 and a[:9] == "--player=":
            player = a[9:]
        elif os.path.isdir(a):
            dir_movies.append(a)
        else:
            omx_args.append(a.strip())
    if test:
        return(True)
    else:
        if len(dir_movies) == 0:
            dir_movies.append(os.path.expanduser("~/movies"))
        if len(omx_args) == 0:
            omx_args = ["-o", "both", "-t", "on", "--align", "center"]
        return(dir_movies, omx_args, player)


class PiMP(object):

    def __init__(self, stdscr):
        "Initialization."
        self.stdscr = stdscr
        self.status = "Ready."
        dir_movies, omx_args, player = parse_args()
        self.player = player
        self.omx_args = omx_args
        self.dir_movies = dir_movies
        self.db = os.path.expanduser("~/.pimp")
        self.init_curses()
        self.reload_database()
        self.get_key_do_action()

    def init_curses(self):
        "Init curses settings."
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        y,x = self.stdscr.getmaxyx()
        self.H = y
        self.W = x

    def reload_database(self, force=None):
        "Reload database (if force, rescan directories)."
        self.init_cursor()
        self.draw_status("Loading library... Please wait!", True)
        self.load_dic_movies(force)
        self.load_lst_movies()
        self.draw_status("Library reloaded.", True)
        self.draw_window()

    def init_cursor(self):
        "Init cursor settings."
        self.cursor = dict()
        self.cursor['current'] = 0
        self.cursor['first'] = 0
        self.cursor['show'] = self.H - 2

    def load_dic_movies(self, force=False):
        "Load dic_movies."
        self.dic_movies = get_movies_from_db(self.db)
        if not self.dic_movies  or force:
            self.dic_movies = get_movies_from_dir_movies(self.dir_movies)
            save_movies_to_db(self.db, self.dic_movies)

    def load_lst_movies(self):
        "Load lst_movies."
        self.lst_movies = list()
        for movie in self.dic_movies:
            self.lst_movies.append(movie)
        self.lst_movies.sort()

    def draw_window(self):
        "Draw window."
        # Cusor of movies to display (first/last)
        first = self.cursor['first']
        last = self.cursor['first'] + self.cursor['show']
        lst_movies = self.lst_movies[first:last]
        # Title of window
        options = " - " + K_PLAY + ":Play " + K_SCAN + ":Refresh "
        options += K_PREV + ":Up " + K_NEXT + ":Down " + K_PPAG 
        options += ":PUp " + K_NPAG + ":PDown " + K_FIND + ":Find "
        options += K_QUIT + ":Quit"
        title = "PiMP V" + str(VERSION) + options
        self.draw_line_of_text(0, title, curses.color_pair(4))
        # List of movies
        self.clear_list_widget(1, self.H-2, self.W-1)
        i = 1
        for movie in lst_movies:
            if movie == self.get_current_movie():
                self.draw_line_of_text(i, "> "+movie, curses.color_pair(2))
            else:
                self.draw_line_of_text(i, "  "+movie)
            i += 1
        # Status
        self.draw_status(self.status)
        self.stdscr.refresh()

    def clear_list_widget(self, start, end, width):
        "Clear the movies list widget."
        i = start
        while i <= end:
            self.draw_line_of_text(i, " ".ljust(width))
            i += 1
            
    def draw_status(self, text, force=False):
        "Draw the status line"
        self.status = text
        self.draw_line_of_text(self.H-1, text[0:self.W-1], curses.color_pair(4))
        if force:
            self.stdscr.refresh()

    def draw_line_of_text(self, pos, text, color=None):
        "Draw a line of text on the window."
        text = text[0:self.W-1]
        if color:
            text = text.ljust(self.W-1, " ")
            self.stdscr.addstr(pos, 0, text, color)
        else:
            self.stdscr.addstr(pos, 0, text)
        self.stdscr.clrtoeol()

    def get_current_movie(self):
        "Return the selected movie."
        return(self.lst_movies[self.cursor['current']])

    def scroll_to(self, offset):
        "Scroll to offset."
        if offset > self.cursor['current']:
            self.scroll_down(offset - self.cursor['current'])
        if offset < self.cursor['current']:
            self.scroll_up(self.cursor['current'] - offset)
        return(True)

    def scroll_up(self, nb_lines):
        "Scroll up the list of movies."
        if self.cursor['current'] >= nb_lines:
            self.cursor['current'] -= nb_lines
        else:
            self.cursor['current'] = 0
        if self.cursor['current'] < self.cursor['first']:
            self.cursor['first'] -= nb_lines

    def scroll_down(self, nb_lines):
        "Scroll down the list of movies."
        if self.cursor['current'] < len(self.lst_movies) - nb_lines - 1:
            self.cursor['current'] += nb_lines
        else:
            self.cursor['current'] = len(self.lst_movies) - 1
        if self.cursor['current'] >= self.cursor['show'] + self.cursor['first']:
            self.cursor['first'] += nb_lines

    def play_selected_movie(self):
        "Play selected movie."
        movie = None
        movie = self.dic_movies[self.lst_movies[self.cursor['current']]]
        if movie:
            self.stdscr.clear()
            self.stdscr.refresh()
            res = play(movie, player=self.player, args=self.omx_args)
            if res:
                self.draw_status("{0}".format(res), True)
            else:
                self.draw_status("Oops!")
        else:
            self.draw_status("Oops! Cannot play selected movie.", True)

    def find_and_scroll(self):
        "Search a movie and scroll to it"
        self.draw_status("Please enter the first letter of the movie.", True)
        # get the first letter to find
        ch = chr(self.stdscr.getch())
        if ch.isalpha():
            # find the first movie begining with this letter
            offset = 0
            find = False
            for movie in self.lst_movies:
                if str(movie[0]).upper() == str(ch).upper():
                    find = True
                    break
                offset += 1
            # scroll to offset
            if find and self.scroll_to(offset):
                self.draw_status("Scrolled to movies starting with '{0}'.".format(ch), True)
            else:
                self.draw_status("Oops! No movies starts with '{0}'.".format(ch), True)
        else:
            self.draw_status("Oops! You didn't type a letter looser.")
            
    def get_key_do_action(self):
        "Event loop."
        while True:
            ch = self.stdscr.getch()
            if ch == curses.KEY_UP or ch == ord(K_PREV):
                self.scroll_up(1)
            elif ch == curses.KEY_DOWN or ch == ord(K_NEXT):
                self.scroll_down(1)
            elif ch == curses.KEY_NPAGE or ch == ord(K_NPAG):
                self.scroll_down(self.H-2)
            elif ch == curses.KEY_PPAGE or ch == ord(K_PPAG):
                self.scroll_up(self.H-2)   
            elif ch == ord(K_PLAY):
                self.play_selected_movie()
            elif ch == ord(K_SCAN):
                self.reload_database(True)
            elif ch == ord(K_QUIT):
                break
            elif ch == ord(K_FIND):
                self.find_and_scroll()
            self.draw_window()


# MAIN PROGRAM 
if __name__ == '__main__':
    if parse_args(test=True):
        app = curses.wrapper(PiMP)
# END MAIN PROGRAM
