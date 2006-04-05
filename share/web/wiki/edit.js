// This is based on the Wikipedia JavaScript support functions
// if this is true, the toolbar will no longer overwrite the infobox when you move the mouse over individual items
var noOverwrite=false;
var alertText;
var clientPC = navigator.userAgent.toLowerCase(); // Get client info
var is_gecko = ((clientPC.indexOf('gecko')!=-1) && (clientPC.indexOf('spoofer')==-1)
                && (clientPC.indexOf('khtml') == -1) && (clientPC.indexOf('netscape/7.0')==-1));
var is_safari = ((clientPC.indexOf('applewebkit')!=-1) && (clientPC.indexOf('spoofer')==-1));
var is_modern_safari = false;

if (is_safari) {
// Figure out if it's a new version of Safari or not
  index = clientPC.lastIndexOf('safari');
  version_number = clientPC.substring(index+7);
  //index = version_number.firstIndexOf('.')
  if (index) {
    index = version_number.indexOf('.')
    version_number = version_number.substring(0, index);
  }
  if (version_number >= 314) {
    is_modern_safari=true;
  }
}

var is_khtml = (navigator.vendor == 'KDE' || ( document.childNodes && !document.all && !navigator.taintEnabled ));
if (clientPC.indexOf('opera')!=-1) {
    var is_opera = true;
    var is_opera_preseven = (window.opera && !document.childNodes);
    var is_opera_seven = (window.opera && document.childNodes);
}

// Un-trap us from framesets
if( window.top != window ) window.top.location = window.location;

innerHTML = '';
innerHTML += addButton('bold.png','Bold text','\'\'\'','\'\'\'','Bold text'); 
innerHTML += addButton('italic.png','Italic text','\'\'','\'\'','Italic text');
innerHTML += addButton('extlink.png','External link','[',']','http://www.example.com');
innerHTML += addButton('head.png','Headline','\n= ',' =\n','Headline text');
innerHTML += addButton('hline.png','Horizontal line (use sparingly)','\n-----\n','','');
innerHTML += addButton('center.png','Center','-->','<--','');
innerHTML += addButton('sig.png','Signature','',' --' + userPageLink,'');
innerHTML += addButton('image.png','Attached image','\n[[Image(',')]]','photo.jpg');
innerHTML += addButton('plain.png','Ignore wiki formatting','{{{','}}}','Insert non-formatted text here');

infoBox = addInfobox('Click a button to get an example text','Please enter the text you want to be formated.\\nIt will be shown in the info box for copy and pasting.\\nExample:\\n$1\\nwill become:\\n$2');
if (!infoBox) {
  innerHTML = '<div id="toolbar">' + innerHTML;
}
else {
  innerHTML = '<div id="toolbarWithInfo">' + innerHTML + infoBox;
}

innerHTML += "</div>";

document.getElementById('search_form').innerHTML = '&nbsp;';
//document.getElementById('iconRow').innerHTML += '<td class="toolbarSize"></td>';

document.getElementById('title').innerHTML += innerHTML;

function addInfobox(infoText,text_alert) {
	alertText=text_alert;
	var clientPC = navigator.userAgent.toLowerCase(); // Get client info

	var re=new RegExp("\\\\n","g");
	alertText=alertText.replace(re,"\n");
        var returnString = "";

	// if no support for changing selection, add a small copy & paste field
	// document.selection is an IE-only property. The full toolbar works in IE and
	// Gecko-based browsers.
	if(!document.selection && !is_gecko && !is_modern_safari) {
 		infoText=escapeQuotesHTML(infoText);
                returnString += '<div style="clear:right;"></div>';
	 	returnString += "<form style=\"position: absolute; display:inline;\" name='infoform' id='infoform'>"+
			"<input id='infobox' class=\"toolbarSize\" name='infobox' value=\""+
			infoText+"\" READONLY></form>";
 	}
        return returnString;
}


// this function generates the actual toolbar buttons with localized text
// we use it to avoid creating the toolbar where javascript is not enabled
function addButton(imageFile, speedTip, tagOpen, tagClose, sampleText) {

	speedTip=escapeQuotes(speedTip);
	tagOpen=escapeQuotes(tagOpen);
	tagClose=escapeQuotes(tagClose);
	sampleText=escapeQuotes(sampleText);
	var mouseOver="";
        var buttonString="";

	// we can't change the selection, so we show example texts
	// when moving the mouse instead, until the first button is clicked
	if(!document.selection && !is_gecko && !is_modern_safari) {
		// filter backslashes so it can be shown in the infobox
		var re=new RegExp("\\\\n","g");
		tagOpen=tagOpen.replace(re,"");
		tagClose=tagClose.replace(re,"");
		mouseOver = "onMouseover=\"if(!noOverwrite){document.infoform.infobox.value='"+tagOpen+sampleText+tagClose+"'};\"";
	}

	buttonString += "<a href=\"javascript:insertTags";
	buttonString += "('"+tagOpen+"','"+tagClose+"','"+sampleText+"');\">";

        buttonString += "<img src=\""+buttonRoot+"/"+imageFile+"\" border=\"0\" ALT=\""+speedTip+"\" TITLE=\""+speedTip+"\""+mouseOver+">";
	buttonString += "</a>";
	return buttonString;
}

function escapeQuotes(text) {
	var re=new RegExp("'","g");
	text=text.replace(re,"\\'");
	re=new RegExp('"',"g");
	text=text.replace(re,'&quot;');
	re=new RegExp("\\n","g");
	text=text.replace(re,"\\n");
	return text;
}

function escapeQuotesHTML(text) {
	var re=new RegExp('"',"g");
	text=text.replace(re,"&quot;");
	return text;
}

// apply tagOpen/tagClose to selection in textarea,
// use sampleText instead of selection if there is none
// copied and adapted from phpBB
function insertTags(tagOpen, tagClose, sampleText) {

	var txtarea = document.editform.savetext;
	// IE
	if(document.selection  && !is_gecko && !is_modern_safari) {
		var theSelection = document.selection.createRange().text;
		if(!theSelection) { theSelection=sampleText;}
		txtarea.focus();
		if(theSelection.charAt(theSelection.length - 1) == " "){// exclude ending space char, if any
			theSelection = theSelection.substring(0, theSelection.length - 1);
			document.selection.createRange().text = tagOpen + theSelection + tagClose + " ";
		} else {
			document.selection.createRange().text = tagOpen + theSelection + tagClose;
		}

	// Mozilla
	} else if(txtarea.selectionStart || txtarea.selectionStart == '0') {
 		var startPos = txtarea.selectionStart;
		var endPos = txtarea.selectionEnd;
		var scrollTop=txtarea.scrollTop;
		var myText = (txtarea.value).substring(startPos, endPos);
		if(!myText) { myText=sampleText;}
		if(myText.charAt(myText.length - 1) == " "){ // exclude ending space char, if any
			subst = tagOpen + myText.substring(0, (myText.length - 1)) + tagClose + " ";
		} else {
			subst = tagOpen + myText + tagClose;
		}
		txtarea.value = txtarea.value.substring(0, startPos) + subst +
		  txtarea.value.substring(endPos, txtarea.value.length);
		txtarea.focus();

		var cPos=startPos+(tagOpen.length+myText.length+tagClose.length);
		txtarea.selectionStart=cPos;
		txtarea.selectionEnd=cPos;
		txtarea.scrollTop=scrollTop;

	// All others
	} else {
		var copy_alertText=alertText;
		var re1=new RegExp("\\$1","g");
		var re2=new RegExp("\\$2","g");
		copy_alertText=copy_alertText.replace(re1,sampleText);
		copy_alertText=copy_alertText.replace(re2,tagOpen+sampleText+tagClose);
		var text;
		if (sampleText) {
			text=prompt(copy_alertText);
		} else {
			text="";
		}
		if(!text) { text=sampleText;}
		text=tagOpen+text+tagClose;
		document.infoform.infobox.value=text;
		// in Safari this causes scrolling
		if(!is_safari) {
			txtarea.focus();
		}
		noOverwrite=true;
	}
	// reposition cursor if possible
	if (txtarea.createTextRange) txtarea.caretPos = document.selection.createRange().duplicate();
}

function akeytt() {
    if(typeof ta == "undefined" || !ta) return;
    pref = 'alt-';
    if(is_safari || navigator.userAgent.toLowerCase().indexOf( 'mac' ) + 1 ) pref = 'control-';
    if(is_opera) pref = 'shift-esc-';
    for(id in ta) {
        n = document.getElementById(id);
        if(n){
            a = n.childNodes[0];
            if(a){
                if(ta[id][0].length > 0) {
                    a.accessKey = ta[id][0];
                    ak = ' ['+pref+ta[id][0]+']';
                } else {
                    ak = '';
                }
                a.title = ta[id][1]+ak;
            } else {
                if(ta[id][0].length > 0) {
                    n.accessKey = ta[id][0];
                    ak = ' ['+pref+ta[id][0]+']';
                } else {
                    ak = '';
                }
                n.title = ta[id][1]+ak;
            }
        }
    }
}
// editor resizing. opera might not work?
var agt=navigator.userAgent.toLowerCase(); 
function sizeTextField(id,e)
{
  var rows = 0;
  var t = document.getElementById(id);
  set_rows = t.rows;
  field_width = t.clientWidth; //with of textarea in px

  if (e.type.toLowerCase() == 'keypress')
  {
    if (e.keyCode != 13) //13 is return key
    {
      return;
    }
    rows = 1;
  }

  var added_new_rows = false;
  //if (e.type.toLowerCase() == 'keypress' || e.type.toLowerCase() == 'onload')
  text_lines = t.value.split('\n');
  for (x = 0; x < text_lines.length; x++)
  {
    text = text_lines[x];

    var hidden_div = document.createElement("div");
    hidden_div.setAttribute('style','visibility:hidden;font-size:110%;display:inline;white-space:nowrap;position:absolute;');
    hidden_div.appendChild(document.createTextNode(text));
    document.getElementById('content').appendChild(hidden_div);
    total_char_width = hidden_div.clientWidth;
    document.getElementById('content').removeChild(hidden_div);
    if (total_char_width > field_width)
    {
      rows += Math.ceil(total_char_width/(field_width));
      added_new_rows = true;
    }
    else
    {
      rows += 1;
    }

  }
  if (rows > t.rows)
  {
    added_new_rows = true;
  }
  if (added_new_rows)
  {
    t.rows = rows + 3;
  }
  //scan through the textarea and calculate the total width of all characters.
  //divide this by the width of the area to obtain the number of rows for the area, roughly.
  
  //convert width in px to number of columns (characters)
  
  //lines = t.value.split('\n');
  //b=1;
  //for (x = 0; x < lines.length; x++)
  //  {
  //    if (lines[x].length >= t.cols) b+= Math.floor(lines[x].length/t.cols);
  //  }
  //b+= lines.length;
  //if (b > t.rows && agt.indexOf('opera') == -1) t.rows = b;
}
