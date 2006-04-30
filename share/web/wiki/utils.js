function preview()
{
if(document.editform != null)
        document.editform.button_preview.click();
}

////////////THIS IS JUST A STRING
var fitScript = "var NS = (navigator.appName=='Netscape')?true:false;\
function fitPic() {\
                                iWidth = (NS)?window.innerWidth:document.body.clientWidth;\
                                iHeight = (NS)?window.innerHeight:document.body.clientHeight;\
                                iWidth = document.images[0].width - iWidth;\
                                iHeight = document.images[0].height - iHeight;\
                                window.resizeBy(iWidth + 20, iHeight + 80);\
                                self.focus();\
};";
///////////END STRING
function hideMessage(id)
{
  if (!document.getElementById) return true;
  msg = document.getElementById(id);
  msg.parentNode.removeChild(msg);
  return false;
}


function imgPopup(caption, imgUrl)
{
win = window.open('', '', 'width=800,height=600,scrollbars=0');
win.document.write("<html><head><title>Image Detail</title><script>" + fitScript + "</script><link rel=\"stylesheet\" type=\"text/css\" charset=\"iso-8859-1\" media=\"all\" href=\"/wiki/eggheadbeta/css/screen.css\"></head><body bgcolor=\"#ffffff\" onload=\"fitPic();\"><center><table class=\"enlarge\"><tr><td><center><img src=\"" + imgUrl + "\"/><div class=\"caption\">" + caption + "</div>[<a href=\"javascript:window.close() \"\">Close Window</a>]</td></tr></table></center></body></html>");
win.document.close();
win.focus();
}
function show(id)
{
var elem = document.getElementById(id);
if(elem != null)
        elem.style.display = '';
}
function hide(id)
{
var elem = document.getElementById(id);
if(elem != null)
        elem.style.display = 'none';
}
function doshow(){ 
        show("map");
        show("hide");
        hide("show");
}
function dohide()
{
  hide("map");
        hide("hide");
        show("show");
}
