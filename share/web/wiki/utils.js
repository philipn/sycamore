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
var elem = document.getElementById(id +'Container');
if(elem != null)
        elem.style.display = '';
}
function hide(id)
{
var elem = document.getElementById(id);
if(elem != null)
        elem.style.display = 'none';
var elem = document.getElementById(id+'Container');
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
function createCookie(name,value,days) {
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
    }
    else var expires = "";
    document.cookie = name+"="+value+expires+"; path=/";
}
function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}
function eraseCookie(name) {
    createCookie(name,"",-1);
}
function canSetCookies()
{
    createCookie('can_set_cookies', 'yes', 1);
    if (readCookie('can_set_cookies'))
    {
        eraseCookie('can_set_cookies');
        return true;
    }
    return false;
}
function authenticateWithFarm()
{
    logout = window.location.href.indexOf('action=userform&logout=Logout');
    if (canSetCookies() && authentication_url && (logout == -1))
    {
        window.location.replace(authentication_url); 
    }
}

authenticateWithFarm();
