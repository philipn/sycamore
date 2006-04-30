// This is based on the Wikipedia JavaScript support functions
// if this is true, the toolbar will no longer overwrite the infobox when you move the mouse over individual items
var noOverwrite=false;
var alertText;
var clientPC = navigator.userAgent.toLowerCase(); // Get client info
var is_gecko = ((clientPC.indexOf('gecko')!=-1) && (clientPC.indexOf('spoofer')==-1)
                && (clientPC.indexOf('khtml') == -1) && (clientPC.indexOf('netscape/7.0')==-1));
var is_safari = ((clientPC.indexOf('applewebkit')!=-1) && (clientPC.indexOf('spoofer')==-1));
var is_modern_safari = false;
var can_alter_textarea = true;

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

toolbar_td = document.createElement('td');
toolbar_innerHTML = '';
toolbar_innerHTML += '<span class="toolbarPaddingStart"></span>';
toolbar_innerHTML += addButton('bold.png','Bold text','\'\'\'','\'\'\'','Bold text'); 
toolbar_innerHTML += addButton('italic.png','Italic text','\'\'','\'\'','Italic text');
toolbar_innerHTML += addButton('extlink.png','External link','[',']','http://www.example.com');
toolbar_innerHTML += addButton('head.png','Headline','\n= ',' =\n','Headline text');
toolbar_innerHTML += addButton('hline.png','Horizontal line (use sparingly)','\n-----\n','','');
toolbar_innerHTML += addButton('center.png','Center','-->','<--','');
toolbar_innerHTML += addButton('sig.png','Signature','',' --' + userPageLink,'');
toolbar_innerHTML += addButton('image.png','Attached image','\n[[Image(',')]]','photo.jpg');
toolbar_innerHTML += addButton('plain.png','Ignore wiki formatting','{{{','}}}','Insert non-formatted text here');

infoBox = addInfobox('Click a button to get an example text','Please enter the text you want to be formated.\\nIt will be shown in the info box for copy and pasting.\\nExample:\\n$1\\nwill become:\\n$2');

toolbar_innerHTML += '<span class="toolbarPaddingEnd"></span>';
if (!infoBox) {
  toolbar_td.setAttribute('id', 'toolbar');
  toolbar_td.innerHTML = toolbar_innerHTML;
}
else {
  toolbar_td.setAttribute('id', 'toolbarWithInfo');
  toolbar_td.innerHTML = toolbar_innerHTML + infoBox;
}

//toolbar_padding = document.createElement('td');
//toolbar_padding.className = 'toolbarSize';
//toolbar_padding.innerHTML = '&nbsp;';
//document.getElementById('iconRow').appendChild(toolbar_padding);
//document.getElementById('iconRow').innerHTML += '<td class="toolbarSize"></td>';
title_element = document.getElementById('title');
title_body = title_element.getElementsByTagName("tbody").item(0);
title_row = title_body.getElementsByTagName("tr").item(0);
//document.getElementById('search_form').innerHTML = '&nbsp;';
title_row.removeChild(document.getElementById('search_form'));
title_row.appendChild(toolbar_td);

//title_element.innerHTML += toolbar_innerHTML;
//title_element.appendChild(document.createTextNode(toolbar_innerHTML));
//title_element.appendChild(document.createTextNode(toolbar_innerHTML));
//title_height = document.getElementById('title').offsetHeight + 10;
//title_text_parent = ((document.getElementById('title_text')).offsetParent);
//title_height = title_text_parent.offsetHeight;

//toolbar_div = document.getElementById(toolbar_id);
//try {
//  toolbar_div.style.cssText('top: '+title_height+'px;');
//}
//catch (e) {
//  toolbar_div.setAttribute('style', 'top: '+title_height+'px;');
//}

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
			"<input id='infobox' style=\"margin-top: 1px;\" class=\"toolbarSize\" name='infobox' value=\""+
			infoText+"\" READONLY></form>";
                can_alter_textarea = false;
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

        buttonString += "<img src=\""+buttonRoot+"/"+imageFile+"\" ALT=\""+speedTip+"\" TITLE=\""+speedTip+"\""+mouseOver+" class=\"editBarIcon\" style=\"behavior: url('" + urlPrefix + "/pngbehavior.htc');\">";
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

function findPosX(obj)
{
    var curleft = 0;
    if (obj.offsetParent)
    {
        while (obj.offsetParent)
        {
            curleft += obj.offsetLeft
            obj = obj.offsetParent;
        }
    }
    else if (obj.x)
        curleft += obj.x;
    return curleft;
}

function findPosY(obj)
{
    var curtop = 0;
    if (obj.offsetParent)
    {
        while (obj.offsetParent)
        {
            curtop += obj.offsetTop
            obj = obj.offsetParent;
        }
    }
    else if (obj.y)
        curtop += obj.y;
    return curtop;
}

function alter_textarea()
{
  document.getElementById('content').removeChild(hidden_div);
  if (global_rows > set_rows)
  {
    t.rows = global_rows + 6;
  }
  else if ((set_rows - global_rows) < 2) //makes sure that we have some padding between the bottom of the textarea and the bottom of the text
  {
     t.rows += 2;
  }
  else
  {
     t.rows = set_rows;
  } 

  set_rows = t.rows;
  
  
  if (event_type == 'load')
  {
    if (can_alter_textarea)
    {
      document.getElementById('editform').removeChild(document.getElementById('editorSize'));
    }

    // make sure we scroll attention to the preview area
    try {
      if (document.getElementById('preview'))
      {
        if (is_safari)
        {
          // Safari (last checked 2.0.3) has an 'never stops loading' issue when doing window.location.href = '#stuff'
          goto_location_x = findPosX(document.getElementById('preview'));
          goto_location_y = findPosY(document.getElementById('preview'));
          window.scrollTo(goto_location_x, goto_location_y);
        }
        else {
          window.location.href = '#preview';
        }
      } 
    }
   catch (e)
   {
      var do_nothing;
   }
  }
}

function calc_line()
{

  if (current_line < text_lines.length)
  {
    for (processed_lines=0; (processed_lines < 20) && (current_line < text_lines.length); processed_lines++)
    {
       rows = 0;
       text = text_lines[current_line];
       hidden_div.innerHTML = text;
       total_char_width = hidden_div.clientWidth;

       if (total_char_width > field_width)
       {
         rows += Math.ceil(total_char_width/(field_width));
         added_new_rows = true;
       }
       else
       {
         rows += 1;
       }

       current_line += 1;
       global_rows += rows;
       //document.getElementsByTagName('body')[0].innerHTML += global_rows + " ";
    }
	

    setTimeout('calc_line()', 30);
    //calc_line();
  }
  else
  {
    alter_textarea();
  }

  return global_rows;
}

var current_line = 0;
var text_lines = [];
var field_width = 0;
var global_rows = 0;
var hidden_div = document.createElement("div");
var t;
var event_type;
var rows;
var set_rows;
var added_new_rows = false;
var textarea_rows;

// editor resizing. opera might not work?
var agt=navigator.userAgent.toLowerCase(); 
function sizeTextField(id,passed_event)
{
  rows = 0;
  event_type = passed_event.type.toLowerCase();
  t = document.getElementById(id);
  set_rows = t.rows;
  field_width = t.clientWidth; //width of textarea in px
  added_new_rows = false;
  current_line = 0;
  global_rows = 0;

  if (event_type == 'load')  // let's set a big textarea and then make it small (probably).  less browser 'pop'
  {
    t.rows = 1000;
  }


  if (event_type == 'keypress')
  {
    if (passed_event.keyCode != 13 || passed_event.which != 13) //13 is return key
    {
      return;
    }
    rows = 1;
  }

  text_lines = t.value.split('\n');
  try
  {
      hidden_div.style.cssText('visibility:hidden;font-size:110%;display:inline;white-space:nowrap;position:absolute;');
  }
  catch (e)
  {
      hidden_div.setAttribute('style','visibility:hidden;font-size:110%;display:inline;white-space:nowrap;position:absolute;');
  }
  document.getElementById('content').appendChild(hidden_div);

  calc_line(); // async call
  

}
