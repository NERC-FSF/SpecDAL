import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
import matplotlib
sys.path.insert(0, os.path.abspath("../.."))
from specdal.containers.spectrum import Spectrum
from collections import Iterable
from specdal.containers.collection import Collection
matplotlib.use('TkAgg')
from datetime import datetime

class Viewer(tk.Frame):
    def __init__(self, parent, collection=None, with_toolbar=True):
        tk.Frame.__init__(self, parent)
        # toolbar
        if with_toolbar:
            self.create_toolbar()
        # canvas
        self.fig = plt.Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.setupMouseNavigation()
        NavigationToolbar2TkAgg(self.canvas, self) # for matplotlib features
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH)
        # spectra list
        self.create_listbox()
        # toggle options
        self.mean = False
        self.median = False
        self.max = False
        self.min = False
        self.std = False
        self.spectrum_mode = False
        self.show_flagged = True
        # data
        self.collection = collection
        self.head = 0
        self.flag_filepath = os.path.abspath('./flagged_spectra.txt')
        if collection:
            self.update_artists(new_lim=True)
            self.update_list()
        # pack
        self.pack()
        self.last_draw = datetime.now()



    def setupMouseNavigation(self):
        def onRectangleDraw(eclick,erelease):
            print("This is a rectangle event!")
            print(eclick.xdata,erelease.xdata)
            if not self.collection is None:
                x_data = self.collection.data.loc[eclick.xdata:erelease.xdata]
                ylim = sorted([eclick.ydata,erelease.ydata])
                is_in_box = ((x_data > ylim[0]) & (x_data < ylim[1])).any()
                #TODO: Pandas builtin
                highlighted = is_in_box.index[is_in_box].tolist()
                print(highlighted)
                key_list = list(self.collection._spectra.keys())

                self.update_selected(highlighted)
                for highlight in highlighted:
                    #O(n^2) woof
                    pos = key_list.index(highlight)
                    self.listbox.selection_set(pos)

        self.rs = RectangleSelector(self.ax, onRectangleDraw, drawtype='none',
                useblit=False, button=[1],spancoords='pixels',
                interactive=False)


    @property
    def head(self):
        return self._head
    @head.setter
    def head(self, value):
        if not hasattr(self, '_head'):
            self._head = 0
        else:
            self._head = value % len(self.collection)
    def set_head(self, value):
        if isinstance(value, Iterable):
            if len(value) > 0:
                value = value[0]
            else:
                value = 0
        self.head = value
        if self.spectrum_mode:
            self.update()
        self.update_selected()

    @property
    def collection(self):
        return self._collection
    @collection.setter
    def collection(self, value):
        if isinstance(value, Spectrum):
            # create new collection
            self._collection = Collection(name=Spectrum.name, spectra=[value])
        if isinstance(value, Collection):
            self._collection = value
        else:
            self._collection = None


    def move_selected_to_top(self):
        selected = self.listbox.curselection()
        keys = [self.collection.spectra[s].name for s in selected]
        for s in selected[::-1]:
            self.listbox.delete(s)
        self.listbox.insert(0,*keys)
        self.listbox.selection_set(0,len(keys))

    def unselect_all(self):
        self.listbox.selection_clear(0,tk.END)
        self.update_selected()

    def select_all(self):
        self.listbox.selection_set(0,tk.END)
        self.update_selected()

    def invert_selection(self):
        for i in range(self.listbox.size()):
            if self.listbox.selection_includes(i):
                self.listbox.selection_clear(i)
            else:
                self.listbox.selection_set(i)
        self.update_selected()

    def create_listbox(self):
        self.scrollbar = ttk.Scrollbar(self)
        self.listbox = tk.Listbox(self, yscrollcommand=self.scrollbar.set,
                                  selectmode=tk.EXTENDED, width=30)
        self.scrollbar.config(command=self.listbox.yview)

        self.list_tools = tk.Frame(self)
        tk.Button(self.list_tools, text="To Top", command = lambda:self.move_selected_to_top()
                ).pack(side=tk.TOP,anchor=tk.NW)
        tk.Button(self.list_tools, text="Select All", command = lambda:self.select_all()
                ).pack(side=tk.TOP,anchor=tk.NW)
        tk.Button(self.list_tools, text="Clear", command = lambda:self.unselect_all()
                ).pack(side=tk.TOP,anchor=tk.NW)
        tk.Button(self.list_tools, text="Invert", command = lambda:self.invert_selection()
                ).pack(side=tk.TOP,anchor=tk.NW)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.list_tools.pack(side=tk.LEFT,anchor=tk.NW)
        self.listbox.bind('<<ListboxSelect>>', lambda x: 
                self.set_head(self.listbox.curselection()))

    def create_toolbar(self):
        self.toolbar = tk.Frame(self)
        tk.Button(self.toolbar, text='Read', command=lambda:
                  self.read_dir()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Mode', command=lambda:
                  self.toggle_mode()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Show/Hide Flagged',
                  command=lambda: self.toggle_show_flagged()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Flag/Unflag', command=lambda:
                  self.toggle_flag()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Unflag all', command=lambda:
                  self.unflag_all()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Save Flag', command=lambda:
                  self.save_flag()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Save Flag As', command=lambda:
                  self.save_flag_as()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Stitch', command=lambda:
                  self.stitch()).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text='Jump_Correct', command=lambda:
                  self.jump_correct()).pack(side=tk.LEFT)       
        tk.Button(self.toolbar, text='mean', command=lambda:
                  self.toggle_mean()).pack(side=tk.LEFT)       
        tk.Button(self.toolbar, text='median', command=lambda:
                  self.toggle_median()).pack(side=tk.LEFT)       
        tk.Button(self.toolbar, text='max', command=lambda:
                  self.toggle_max()).pack(side=tk.LEFT)       
        tk.Button(self.toolbar, text='min', command=lambda:
                  self.toggle_min()).pack(side=tk.LEFT)       
        tk.Button(self.toolbar, text='std', command=lambda:
                  self.toggle_std()).pack(side=tk.LEFT)       
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

    def set_collection(self, collection):
        new_lim = True if self.collection is None else False
        self.collection = collection
        self.update_artists(new_lim=new_lim)
        self.update()
        self.update_list()

    def read_dir(self):
        directory = filedialog.askdirectory()
        if not directory:
            return
        c = Collection(name="collection", directory=directory)
        self.set_collection(c)
    def toggle_mode(self):
        if self.spectrum_mode:
            self.spectrum_mode = False
        else:
            self.spectrum_mode = True
        self.update()
    def toggle_show_flagged(self):
        if self.show_flagged:
            self.show_flagged = False
        else:
            self.show_flagged = True
        self.update()
    def unflag_all(self):
        for spectrum in list(self.collection.flags):
            self.collection.unflag(spectrum)
        self.update()
        self.update_list()

    def toggle_flag(self):
        selected = self.listbox.curselection()
        keys = [self.listbox.get(s) for s in selected]
        
        for i,key in enumerate(keys):
            print(i,key)
            spectrum = key
            if spectrum in self.collection.flags:
                self.collection.unflag(spectrum)
                self.listbox.itemconfigure(selected[i], foreground='black')
            else:
                self.collection.flag(spectrum)
                self.listbox.itemconfigure(selected[i], foreground='red')
        # update figure
        self.update()
    def save_flag(self):
        ''' save flag to self.flag_filepath'''
        with open(self.flag_filepath, 'w') as f:
            for spectrum in self.collection.flags:
                print(spectrum, file=f)
    def save_flag_as(self):
        ''' modify self.flag_filepath and call save_flag()'''
        flag_filepath = filedialog.asksaveasfilename()
        if os.path.splitext(flag_filepath)[1] == '':
            flag_filepath = flag_filepath + '.txt'
        self.flag_filepath = flag_filepath
        self.save_flag()

    def update_list(self):
        self.listbox.delete(0, tk.END)
        for i, spectrum in enumerate(self.collection.spectra):
            self.listbox.insert(tk.END, spectrum.name)
            if spectrum.name in self.collection.flags:
                self.listbox.itemconfigure(i, foreground='red')
        self.update_selected()
    
    def ask_for_draw(self):
        #debounce canvas updates
        now = datetime.now()
        print(now-self.last_draw)
        if((now-self.last_draw).total_seconds() > 0.5):
            self.canvas.draw()
            self.last_draw = now

    def update_artists(self,new_lim=False):
        if self.collection is None:
            return
        # save limits
        if new_lim == False:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
        # plot
        self.ax.clear()
        # show statistics
        if self.spectrum_mode:
            idx = self.listbox.curselection()
            if len(idx) == 0:
                idx = [self.head]
            spectra = [self.collection.spectra[i] for i in idx]
            flags = [s.name in self.collection.flags for s in spectra]
            print("flags = ", flags)
            flag_style = ' '
            if self.show_flagged:
                flag_style = 'r'
            artists = Collection(name='selection', spectra=spectra).plot(ax=self.ax,
                         style=list(np.where(flags, flag_style, 'k')),
                         picker=1)
            self.ax.set_title('selection')            
            # c = str(np.where(spectrum.name in self.collection.flags, 'r', 'k'))
            # spectrum.plot(ax=self.ax, label=spectrum.name, c=c)
        else:
            # red curves for flagged spectra
            flag_style = ' '
            if self.show_flagged:
                flag_style = 'r'
            flags = [s.name in self.collection.flags for s in self.collection.spectra]
            print("flags = ", flags)
            self.collection.plot(ax=self.ax,
                                 style=list(np.where(flags, flag_style, 'k')),
                                 picker=1)
            self.ax.set_title(self.collection.name)

        keys = [s.name for s in self.collection.spectra]
        artists = self.ax.lines
        self.artist_dict = {key:artist for key,artist in zip(keys,artists)}

        '''
        def onpick(event):
            spectrum_name = event.artist.get_label()
            pos = list(self.collection._spectra.keys()).index(spectrum_name)
            self.listbox.selection_set(pos)
        self.fig.canvas.mpl_connect('pick_event', onpick)
        '''

    def update_selected(self,to_add=None):
        """ Update, only on flaged"""
        if self.collection is None:
            return

        if to_add:
            for key in to_add:
                self.artist_dict[key].set_linestyle('--')
        else:
            keys = [s.name for s in self.collection.spectra]
            selected = self.listbox.curselection()
            selected_keys = [self.collection.spectra[s].name for s in selected]
            for key in keys:
                if key in selected_keys:
                    self.artist_dict[key].set_linestyle('--')
                else:
                    self.artist_dict[key].set_linestyle('-')
        self.canvas.draw()


    def update(self):
        """ Update the plot """
        if self.collection is None:
            return
        # show statistics
        if self.spectrum_mode:
            print("Not implemented!")
            """
            idx = self.listbox.curselection()
            if len(idx) == 0:
                idx = [self.head]
            spectra = [self.collection.spectra[i] for i in idx]
            flags = [s.name in self.collection.flags for s in spectra]
            print("flags = ", flags)
            flag_style = ' '
            if self.show_flagged:
                flag_style = 'r'
            Collection(name='selection',
                       spectra=spectra).plot(ax=self.ax,
                                             style=list(np.where(flags, flag_style, 'k')),
                                             picker=1)
            self.ax.set_title('selection')            
            # c = str(np.where(spectrum.name in self.collection.flags, 'r', 'k'))
            # spectrum.plot(ax=self.ax, label=spectrum.name, c=c)
            """
        else:
            # red curves for flagged spectra

            keys = [s.name for s in self.collection.spectra]
            for key in keys:
                if key in self.collection.flags:
                    if self.show_flagged:
                        self.artist_dict[key].set_visible(True)
                        self.artist_dict[key].set_color('red')
                    else:
                        self.artist_dict[key].set_visible(False)
                else:
                    self.artist_dict[key].set_color('black')

            '''
            self.collection.plot(ax=self.ax,
                                 style=list(np.where(flags, flag_style, 'k')),
                                 picker=1)
            self.ax.set_title(self.collection.name)
            '''
            
        if self.mean:
            self.collection.mean().plot(ax=self.ax, c='b', label=self.collection.name + '_mean')
        if self.median:
            self.collection.median().plot(ax=self.ax, c='g', label=self.collection.name + '_median')
        if self.max:
            self.collection.max().plot(ax=self.ax, c='y', label=self.collection.name + '_max')
        if self.min:
            self.collection.min().plot(ax=self.ax, c='m', label=self.collection.name + '_min')
        if self.std:
            self.collection.std().plot(ax=self.ax, c='c', label=self.collection.name + '_std')
        # reapply limits
        # legend
        if self.spectrum_mode:
            self.ax.legend()
        else:
            self.ax.legend().remove()
        self.ax.set_ylabel(self.collection.measure_type)
        self.canvas.draw()

    def next_spectrum(self):
        if not self.spectrum_mode:
            return
        self.head = (self.head + 1) % len(self.collection)
        self.update()
    def stitch(self):
        ''' 
        Known Bugs
        ----------
        Can't stitch one spectrum and plot the collection
        '''
        self.collection.stitch()
        self.update()
    def jump_correct(self):
        ''' 
        Known Bugs
        ----------
        Only performs jump correction on 1000 and 1800 wvls and 1 reference
        '''
        self.collection.jump_correct([1000, 1800], 1)
        self.update()
    def toggle_mean(self):
        if self.mean:
            self.mean = False
        else:
            self.mean = True
        self.update()
    def toggle_median(self):
        if self.median:
            self.median = False
        else:
            self.median = True
        self.update()
    def toggle_max(self):
        if self.max:
            self.max = False
        else:
            self.max = True
        self.update()
    def toggle_min(self):
        if self.min:
            self.min = False
        else:
            self.min = True
        self.update()
    def toggle_std(self):
        if self.std:
            self.std = False
        else:
            self.std = True
        self.update()

def read_test_data():
    path = '~/data/specdal/aidan_data2/ASD'
    c = Collection("Test Collection", directory=path)
    for i in range(30):
        c.flag(c.spectra[i].name)

def main():
    root = tk.Tk()
    v = Viewer(root, None)
    v.update()
    root.mainloop()


if __name__ == "__main__":
    main()
