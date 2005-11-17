#Dependencies = []

def execute(macro, args):
    return macro.formatter.rawHTML('<script language="JavaScript">function addEngine(name,icon,cat){if ((typeof window.sidebar == "object") && (typeof window.sidebar.addSearchEngine == "function")){var iconPath;if(icon != "" && icon != undefined){iconPath = "http://daviswiki.org/cool_files/firefox/"+icon;}window.sidebar.addSearchEngine("http://daviswiki.org/cool_files/firefox/"+name+".src",iconPath,name,cat );}else{alert("The Firefox browser is required to install this plugin.");}}</script><a href="javascript:addEngine(\'daviswiki\',\'daviswiki.png\',\'Web\')"><img src="http://daviswiki.org/cool_files/firefox/daviswiki.png"/>&nbsp;Install the Davis Wiki search plugin!</a>')
