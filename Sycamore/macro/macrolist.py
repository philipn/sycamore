#
# This is a list of macros, to automate the 
# macros list page by reading the macros directory
#
# FarMcKon <FarMcKon@gmail.com> April 2007


import re
import os 

Dependencies = []

##
# @param args  A string containing all of the text in the macro
# @param macro  Some kind of Sycamore magic
# @param formatter Some kind of Sycamore magic
#
def execute(macro, args, formatter=None):

	macroList = [] # a list of lists of text [ Title, MacroFormat, infoText]
	outputText = [] #output preformatter text

	#Heart has no () and therfore has no args 
    
	if not formatter:
		formatter = macro.formatter

	macroList = buildMacroList()
	
	if(len(macroList) != 0):
		outputText.append('<ul>')	

	for macroItem in macroList:
		outputText.append("<li>")
		outputText.append( macroItem[0]) #name
		outputText.append(" - [[")
		outputText.append( macroItem[1]) #format example
		outputText.append("]] : ")
		outputText.append( macroItem[2]) #description of format example
		outputText.append('</li>')
		#return formatter.rawHTML('&hearts;')
	
	if(len(macroList) != 0):
		outputText.append('</ul>')	
		return formatter.rawHTML(''.join(outputText))
		#return formatter.number_list(macroList)

	return formatter.rawHTML('No Macro List Found')
	

# returns a list of list(2). Each list(2) contains 3 items,
# "MacroName", "MacroFormat", "macro description"
# a single macro can have multiple entries, based on the values that can be passed to it
#
# @param none
# @return A list of lists(2) as described above  
def buildMacroList():

	# static temp list for testing
	macroList = [] # a list of lists of text [ Title, MacroFormat, infoText]
	macroList.append(["Anchor","Anchor(anchorName)","Creates an anchor on the page."])
     	macroList.append(["Comments","Comments(Leave your comments here)","Creates a comment box with heading 'Leave your...'"])
 	#macroList.

	macroList = getMacrosFromDir("/home/farmckon/sycamore_base/Sycamore/macro")

	return macroList


# Generates a dynamic list of macros from a listing of files in a directory
# this is an earily version, no capitalization, etc built in  
def getMacrosFromDir(dir):
	macroList = [["a","b","c"]]
	# generate dynamic list
	for file in [f for f in os.listdir(dir)
		if f.lower().endswith('.py') and not f.startswith('__')]:
			try:
				macroName = file.lower().replace('.py','')
				macroExamp = "no example use"
				macroInfo =  "no example info"
				#module = imp.load_source(file[:-3], os.path.join(dir, file))
				macroList.append([macroName,macroExamp,macroInfo])
			except Exception:
  				pass

	return macroList
