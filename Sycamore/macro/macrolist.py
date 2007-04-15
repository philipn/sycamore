#
# This is a list of macros, to automate the 
# macros list page by reading the macros directory
#
# FarMcKon <FarMcKon@gmail.com> April 2007


import re
import os 

Dependencies = []

##
# @macro MacroList()
#	Scans the Macro directory, and lists all Macros
# @macro MacroList(MacroName)
#	Scans the Macro directory, and lists all macros and options that match MacroName
#	(currently not implemented
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

	# a static temp list for testing (needs to go away
	macroList = [] # a list of lists of text [ Title, MacroFormat, infoText]
	macroList.append(["Anchor","Anchor(anchorName)","Creates an anchor on the page."])
     	macroList.append(["Comments","Comments(Leave your comments here)","Creates a comment box with heading 'Leave your...'"])

	macroList = getMacrosFromDir("/home/farmckon/sycamore_base/Sycamore/macro")

	return macroList

##
# Generates a dynamic list of macros from a listing of files in a directory
# this is an earily version, no capitalization, etc built in  
def getMacrosFromDir(dir):
	macroList = [["tmp","for","testing"]]
	# generate dynamic list
	for file in [f for f in os.listdir(dir)
		if f.lower().endswith('.py') and not f.startswith('__')]:
			try:
				macroName = file.lower().replace('.py','')
				macroExamp = "no example use"
				macroInfo =  "no example info"
				test = getMacroInfoFromFile(dir + '/'+ file)
				if(len(test) != 0):
					for example in test:
						if(example[0] != None) and (example[1] != None):	
							tmpA = example[0]
							tmpB = example[1]
							macroList.append([macroName,tmpA,tmpB])
				else: #len(test) == 0
					macroList.append([macroName,macroExamp,macroInfo])
					
			except Exception:
  				pass

	return macroList

##
# This function opens the passed file, and scans for a comment block starting ## 
# that appears about a function 'execute'. When it finds that, it scans the comment 
# for "@ macro" and reads the text off lines that match as 'macroExamp', and it 
# reads text off following indented lines as 'macroInfo'. It then makes a list of all macroExamp/macroInfo pairs
# and returns them.
def getMacroInfoFromFile(inFile):
	macroInfoList = []
	fileLines = []
	bookmark = -1
	execute = -1
	try:
		file = open(inFile,'r')
		fileLines = file.readlines()
		file.close()
	except Execption:
		pass

	#start scanning. Look for ## to 'bookmark' and 'def execute' to start processing
	for lineNum, line  in enumerate (fileLines):
		if(line.find("##") != -1):
			bookmark = lineNum
			continue
		if(line.find("def execute") != -1):
			execute = lineNum
			break;


	# if these are met, we have a comment to search
	if((bookmark != -1) and (execute != -1) and (execute > bookmark)):
		macroInfoList.append(['example found',"... but can't read"])
		started = 0
		tmpExamp = None
		tmpInfo = None
		for line in commentBlock:
			if(line.find("@macro") != -1):
				commentBlock = fileLines[bookmark:execute+1]
				tmpExamp = line.replace("@macro",'').lstrip('#').rstrip().lstrip()
				started = 1
			elif (line.find("#") and (started == 1)):
				tmpInfo += line.lstrip('#').listrip().rstrip()
			else: 
				started = 0
				if(tmpInfo != None) and (tmpExamp != None):
					macroInfoList.append([tmpInfo,tmpExamp])
					tmpInfo = None
					tmpExamp = None
	return macroInfoList
