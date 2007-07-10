var can_alter_textarea = true;
var RC_LIST_THRESHOLD = 15;
if ((navigator.appName == 'Microsoft Internet Explorer') && (parseInt(navigator.appVersion) <= 6))
    is_ie_6_or_less = true;
else
    is_ie_6_or_less = false;

//Get all the elements of the given classname of the given tag.
function getElementsByClassName(classname,tag) {
 if(!tag) tag = "*";
 var anchs =  document.getElementsByTagName(tag);
 var total_anchs = anchs.length;
 var regexp = new RegExp('\\b' + classname + '\\b');
 var class_items = new Array()
 
 for(var i=0;i<total_anchs;i++) { //Go thru all the links seaching for the class name
  var this_item = anchs[i];
  if(regexp.test(this_item.className)) {
   class_items.push(this_item);
  }
 }
 return class_items;
}

function preview()
{
if(document.editform != null)
        document.editform.button_preview.click();
}

function hideMessage(id)
{
  if (!document.getElementById) return true;
  msg = document.getElementById(id);
  msg.parentNode.removeChild(msg);
  return false;
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

function screenPosY()
{
    if (window.innerHeight)
        pos = window.pageYOffset;
    else if (document.documentElement && document.documentElement.scrollTop)
        pos = document.documentElement.scrollTop;
    else if (document.body)
        pos = document.body.scrollTop;
    else
        pos = 0;

    return pos;
}

function alter_textarea()
{
  document.getElementById('content').removeChild(hidden_div);
  if (global_rows > set_rows)
  {
    t.rows = global_rows + 2;
  }
  else if ((set_rows - global_rows) < 2) //makes sure that we have some padding between the bottom of the textarea and the bottom of the text
  {
     t.rows += 1;
  }
  else
  {
     t.rows = set_rows;
  } 

  set_rows = t.rows;
  
  
  if (event_type == 'load')
  {
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
  if (passed_event)
  {
    event_type = passed_event.type.toLowerCase();
  }
  else
  {
    event_type = 'load';
  }
  t = document.getElementById(id);
  set_rows = t.rows;
  field_width = t.clientWidth; //width of textarea in px
  added_new_rows = false;
  current_line = 0;
  global_rows = 0;

  //if (event_type == 'load')  // let's set a big textarea and then make it small (probably).  less browser 'pop'
  //{
  //  t.rows = 10;
  //}
  if (event_type == 'keypress')
  {
    if (passed_event.keyCode != 13 && passed_event.which != 13) //13 is return key
    {
      return;
    }
    rows = 1;
  }
  text_lines = t.value.split('\n');
  try
  {
      hidden_div.style.cssText = 'visibility:hidden;font-size:110%;display:inline;white-space:nowrap;position:absolute;';
  }
  catch (e)
  {
      hidden_div.setAttribute('style','visibility:hidden;font-size:110%;display:inline;white-space:nowrap;position:absolute;');
  }
  document.getElementById('content').appendChild(hidden_div);
  calc_line(); // async call
}

var editAreaContentName;
var editing_now = false;

function getInlineEditAreas(area, next_id)
{
    if (area.nodeName == 'P')
    {
        start_loc = parseInt(area.id.substring(1));
        loc = start_loc;
        if (area.parentNode.parentNode.nodeName != 'LI') {
            for (i=start_loc; ((wikiLines[i-1] != '') && ((i-1) < wikiLines.length) && (loc < next_id)); i++) 
            {
                if ((wikiLines[i-1].substring(0,4) == '----')) {
                    break;
                }
                loc++;
            }
        }
        else
            loc += 1;

        inlineEdit(start_loc, loc-1)
    }
    else
    {
        loc = parseInt(area.id.substring(1));
        inlineEdit(loc, loc);
    }
}


function getNextId(id)
{
    start_id = id;
    for (i = id; i <= wikiLines.length; i++) {
      id++; 
      try {
          elm = document.getElementById('l' + id.toString());
          if (elm)
             break;
      }
      catch (e) {
      }
    }
    return id;
}

var process_chunk_size = 30;
function createClickProperties(start)
{
    if (!may_inline_edit)
        return false;
    var i, j;
    for (i = start, j = 0; i < wikiLines.length && j < process_chunk_size; i++, j++)
    {
        line = wikiLines[i-1];
        spanWithLine = document.createElement("div");
        spanWithLine.setAttribute('title', "Double click here to edit!");
        try
        {
            contentLine = document.getElementById('l'+i.toString());
            next_id = getNextId(i);
            if (contentLine.nodeName == 'TR')
            {
                contentLine.setAttribute('title', "Double click to edit!");
                function attachFunction(contentLine, next_id) {
                    var contentLine = contentLine;
                    return function () { getInlineEditAreas(contentLine, next_id) };
                }
                contentLine.ondblclick = attachFunction(contentLine, next_id);
            }
            else
            {
                contentLine.parentNode.replaceChild(spanWithLine, contentLine);
                function attachFunction(contentLine, next_id) {
                    var contentLine = contentLine;
                    return function () { getInlineEditAreas(contentLine, next_id) };
                }
                contentLine.ondblclick = attachFunction(contentLine, next_id);
                spanWithLine.appendChild(contentLine);
            }
        }
        catch (e)
        {
        }
    }
    if (i < wikiLines.length) {
        setTimeout('createClickProperties(' + i + ');', 100);
    }
}

function createEditSubmit()
{
    if (!may_inline_edit)
        return false;
    document.getElementById('content').innerHTML += '<div style="display: none;"><form name="editform" id="editform" method="post" action="' + action + '"><input type="hidden" name="action" value="savepage"><input type="hidden" name="datestamp" value="' + curTimestamp + '"><input type="text" name="screenposy" style="display: none;"><textarea id="savetext" name="savetext" style="display: none;"></textarea><input type="submit" name="button_save" value="Save Changes" style="display: none;"><input type="hidden" name="comment" value="(quick edit)"><input type="hidden" name="no_save_msg" value="1"></form></div>';
}

function createEditAskArea(id_start, id_end, type)
{
    type = type || '';
    var editAsk = document.createElement("div");
    editAsk.innerHTML = '<form name="inlineEditAsk" id="inlineEditAsk'+id_start+'" method="post" action="/Front_Page"><input type="button" class="formbutton" name="button_edit" value="Edit" onClick="setupEdit(' + id_start + ',' + id_end + ')"><input type="button" class="formbutton" name="button_cancel" value="Cancel" onClick="cancelEditAsk(' + id_start + ',' + id_end + ',\'' + type + '\')"></form>';
    return editAsk;
}

function createEditSaveArea(id_start, id_end, type)
{
    var editAskSave = document.createElement("div");
    editAskSave.innerHTML = '<form name="inlineEdit'+id_start+'" id="inlineEdit'+id_start+'" method="post" action="/Front_Page"><input type="button" class="formbutton" name="button_edit" value="Save" onChange="" onSelect="" onPaste="" onFocus="" onKeyPress="" onClick="saveEdit(' + id_start + ',' + id_end + ')"><input type="button" class="formbutton" name="button_cancel" value="Cancel" onChange="" onSelect="" onPaste="" onFocus="" onKeyPress="" onClick="cancelEdit(' + id_start + ',' + id_end + ',' + '\'' + type + '\')"></form>';
    return editAskSave;
}


function mergeTables(at_table, before_table, after_table, attachFunction)
{
    if (before_table) {
        table = before_table.cloneNode('true'); 
        row = at_table.getElementsByTagName('TR')[0];
        table_body = table.getElementsByTagName('TBODY')[0]
        if (!table_body) table_body = table;
        table_body.appendChild(row);
    }
    else {
        table = at_table.cloneNode('true');
    }

    if (table.childNodes[0].nodeName == 'TBODY' || (table.childNodes.length > 1 && table.childNodes[1].nodeName == 'TBODY'))
        table_body = table.getElementsByTagName('tbody')[0];
    else
        table_body = table

    for (i = 0; i < table_body.childNodes.length; i++)
        if (table_body.childNodes[i].nodeName == 'TR')
            table_body.childNodes[i].setAttribute('title', "Double click here to edit!");

    if (after_table) {
        if (after_table.childNodes[0].nodeName == 'TBODY' || after_table.childNodes[1].nodeName == 'TBODY')
            after_table_body = after_table.getElementsByTagName('tbody')[0];
        else
            after_table_body = after_table;
        for (i = 0; i < after_table_body.childNodes.length; i++)
        {
            elm = after_table_body.childNodes[i].cloneNode('true');
            if (elm.nodeName == 'TR')
                elm.ondblclick = attachFunction(elm.id.substring(1), elm.id.substring(1));
            table_body.appendChild(elm);
        }
        if (after_table.nodeName == 'TABLE') {
            for (i = 0; i < after_table.attributes.length; i++)
            {
                table.setAttribute(after_table.attributes[i].nodeName, after_table.attributes[i].nodeValue);
            }
        }
    }

    for (i = 0; i < table.getElementsByTagName('tr').length; i++)
        table.getElementsByTagName('tr')[i].is_split = undefined;;

    return table;
}

function cancelEditAsk(id_start, id_end, type)
{
    type = type || '';
    editAreaContent = document.getElementById('l'+id_start.toString());
    editArea = editAreaContent.parentNode;
    editAreaContent.className = '';
    function attachFunction(id_start, id_end) {
        var id_start = id_start;
        var id_end = id_end;
        return function () { inlineEdit(id_start, id_end); };
    }
    editAreaContent.ondblclick = attachFunction(id_start, id_end);
    if (type == '') {
        editArea.removeChild(editAreaContent);
        editArea.parentNode.replaceChild(editAreaContent, editArea);
    }
    else { 
        afterEditArea = editAreaContent.parentNode.parentNode.nextSibling;
        beforeEditArea = editAreaContent.parentNode.parentNode.previousSibling;

        if (!afterEditArea || !afterEditArea.is_split)
            afterEditAreaTable = undefined;
        else
            afterEditAreaTable = afterEditArea.getElementsByTagName('table')[0];

        if (!beforeEditArea || !beforeEditArea.is_split)
            beforeEditAreaTable = undefined;
        else
            beforeEditAreaTable = beforeEditArea.getElementsByTagName('table')[0];

        table = mergeTables(editArea, beforeEditAreaTable, afterEditAreaTable, attachFunction);
        if (afterEditArea) afterEditArea.parentNode.removeChild(afterEditArea);
        if (beforeEditArea) beforeEditArea.parentNode.removeChild(beforeEditArea);
        editArea.parentNode.replaceChild(table, editArea);
        //remove edit submit buttons
        edit_cancel_area = document.getElementById('inlineEditAsk' + id_start)
        edit_cancel_area.parentNode.removeChild(edit_cancel_area);

        if (table.childNodes[0].nodeName == 'TBODY')
            table_body = table.childNodes[0];
        else if (table.childNodes[1].nodeName == 'TBODY')
            table_body = table.childNodes[1];
        else
            table_body = table;

        for (i = 0; i < table_body.childNodes.length; i++)
        {
            elm = table_body.childNodes[i];
            if (elm.nodeName == 'TR') {
                tr_id_start = elm.id.substring(1);
                tr = document.getElementById('l'+tr_id_start);
                if (tr) tr.ondblclick = attachFunction(tr_id_start, tr_id_start);
            }
        }

    }
}

function cancelEdit(id_start, id_end, type)
{
    editing_now = false;
    editAreaContent = document.getElementById('l'+id_start.toString());
    editArea = editAreaContent.parentNode;
    old_html_content = wikiLinesHTML.getAttribute('l'+id_start.toString()).replace('\n','');
    if (type == 'TR') {
        placeholder = document.createElement('div');
        placeholder.innerHTML = old_html_content;
        newEditAreaContent = placeholder;
        newEditAreaContent.className = 'wikitable';

        /* Merge before/after together and then kill 'em */
        afterEditArea = editArea.nextSibling;
        beforeEditArea = editArea.previousSibling;
        editAreaContent.innerHTML = old_html_content;

        if (!afterEditArea || !afterEditArea.is_split) afterEditArea = undefined;
        if (!beforeEditArea || !beforeEditArea.is_split) beforeEditArea = undefined;
        function attachFunction(id_start, id_end) {
            var id_start = id_start;
            var id_end = id_end;
            return function () { inlineEdit(id_start, id_end); };
        }
        editAreaContent.getElementsByTagName('TR')[0].id = 'l'+id_start.toString();
        editAreaContent.getElementsByTagName('TR')[0].ondblclick = attachFunction(id_start, id_end);
        editAreaContent.getElementsByTagName('TR')[0].setAttribute('title', "Double click here to edit!");

        if (afterEditArea) afterEditArea.parentNode.removeChild(afterEditArea);
        if (beforeEditArea) beforeEditArea.parentNode.removeChild(beforeEditArea);

        editArea.removeChild(editAreaContent);
        editArea.parentNode.parentNode.replaceChild(newEditAreaContent, editArea.parentNode);
        if (beforeEditArea) {
            tableBefore_rows = beforeEditArea.getElementsByTagName('TR');
            for (i = 0; i < tableBefore_rows.length; i++)
            {
                tr_id_start = tableBefore_rows[i].id.substring(1);
                tr = document.getElementById('l'+tr_id_start);
                tr.ondblclick = attachFunction(tr_id_start, tr_id_start);
            }
        }
        if (afterEditArea) {
            tableAfter_rows = afterEditArea.getElementsByTagName('TR');
            for (i = 0; i < tableAfter_rows.length; i++)
            {
                tr_id_start = tableAfter_rows[i].id.substring(1);
                tr = document.getElementById('l'+tr_id_start);
                if (tr)
                    tr.ondblclick = attachFunction(tr_id_start, tr_id_start);
            }
        }
        document.getElementById('l'+id_start.toString()).ondblclick = attachFunction(id_start, id_start);

    }
    else {
        newEditAreaContent = document.createElement(type);
        newEditAreaContent.id = 'l' + id_start.toString();
        function attachFunction(id_start, id_end) {
            var id_start = id_start;
            var id_end = id_end;
            return function () { inlineEdit(id_start, id_end); };
        }
        newEditAreaContent.ondblclick = attachFunction(id_start, id_end);
        newEditAreaContent.innerHTML = old_html_content;
        editArea.removeChild(editAreaContent);
        editArea.parentNode.replaceChild(newEditAreaContent, editArea);
        newEditAreaContent.parentNode.setAttribute('title', 'Double click here to edit!');
    }
    try {
        editAreaContent.style.cssText('');
    }
    catch (e) {
        editAreaContent.setAttribute('style', '');
    }
    if (is_ie_6_or_less)
        window.onresize = undefined;
}

function saveEdit(id_start, id_end)
{
    id = 'inlineEditTextArea' + id_start.toString();
    editing_now = false;
    textarea = document.getElementById(id);
    newWikiText = textarea.value;
    before_area = '';
    for (i = 0; i < id_start-1; i++)
      before_area += wikiLines[i] + '\n';
    after_area = '';
    for (j = id_end; j < wikiLines.length; j++)
      after_area += wikiLines[j] + '\n';

    saveText = before_area + newWikiText + '\n' + after_area;
    document.getElementById('savetext').value = saveText;
    document.editform.screenposy.value = screenPosY();
    document.editform.button_save.click();
}

function backupWikiText(id_start, id_end, html_to_save)
{
    wikiText = '';
    for (i = id_start; i <= id_end; i++)
    {
        if (wikiText != '') wikiText += '\n'
        wikiText += wikiLines[i-1];
    }
    wikiLinesHTML.setAttribute('l'+id_start.toString(), html_to_save);
}

function make_ie_textarea_percent(textarea, percent)
{
    textarea.style.cssText = 'width:' + percent.toString() + '%;';
    amount = textarea.clientWidth;
    if (textarea.nodeName == 'TEXTAREA') { // IE seems to give extra padding to the right, so let's adjust.
        amount += 8; // 8 pixels seems to be the sweet spot.  More than this and we cause a scrollbar to appear.
    }
    textarea.style.cssText = 'width:' + amount + 'px;';
}

function sizeForIE(id1, percent1, id2, percent2)
{
    if (is_ie_6_or_less) {
        area1 = document.getElementById(id1);
        make_ie_textarea_percent(area1, percent1);
        area2 = document.getElementById(id2);
        make_ie_textarea_percent(area2, percent2);
        window.onresize = function () { sizeForIE(id1, percent1, id2, percent2);};
    } 
}

function setupEdit(id_start, id_end)
{
    if (editing_now) {
       alert("You're already editing an area of the page.  You can only edit one at a time!");
       return;
    }
    editing_now = true;
    editAreaContentName = editAreaContent.nodeName;
    editAreaContent = document.getElementById('l' + id_start.toString());
    editAreaContentParent = editAreaContent.parentNode;
    editArea = document.createElement("div");
    editArea.id = editAreaContent.id;
    editAreaContent.innerHTML = '';
    textArea = document.createElement("textarea");
    textArea.id = 'inlineEditTextArea' + id_start;
    
    wikiEditText = document.createTextNode(wikiText);
    textArea.appendChild(wikiEditText);
    editAsk = document.getElementById('inlineEditAsk'+id_start);

    editSaveArea = createEditSaveArea(id_start, id_end, editAreaContent.nodeName);

    editAsk.parentNode.removeChild(editAsk);
    editArea.appendChild(textArea);
    editArea.appendChild(editSaveArea);
    editAreaContentParent.appendChild(editArea);
    //editAreaContentParent.removeChild(editAreaContent);

    if (editAreaContent.nodeName == 'TR') {
        table = editAreaContentParent.parentNode.getElementsByTagName('table')[0];
        table.parentNode.replaceChild(table.getElementsByTagName('div')[0], table);
    }

    content_width = document.getElementById('content').clientWidth - findPosX(document.getElementById('content'));
    edit_area_pos = findPosX(editArea) - findPosX(document.getElementById('content'));
    try
    {
        editAreaContent.style.cssText = '';
        textArea.style.cssText = 'width: 100%;';
        editArea.style.cssText = 'overflow:hidden;position:relative;left:-' + edit_area_pos + 'px;';
    }
    catch (e)
    {
      editAreaContent.setAttribute('style','');
      textArea.setAttribute('style','width:100%;');
      editArea.setAttribute('style','overflow:hidden;position:relative;left:-' + edit_area_pos + 'px;');
    }

    if (is_ie_6_or_less) {
        make_ie_textarea_percent(textArea, 100);
        window.onresize = function () { make_ie_textarea_percent(textArea, 100) };
    }

    //textArea.onchange = function (e) { if (!e) var e = window.event; sizeTextField(textArea.id,e); };
    // onchange here was causing weird toggle on cancel/save buttons.  it's probably a good idea, tho
    textArea.onselect = function (e) { if (!e) var e = window.event; sizeTextField(textArea.id,e); };
    textArea.onpaste = function (e) { if (!e) var e = window.event; sizeTextField(textArea.id,e); };
    textArea.onfocus = function (e) { if (!e) var e = window.event; sizeTextField(textArea.id,e); };
    textArea.onkeypress = function (e) { if (!e) var e = window.event; sizeTextField(textArea.id,e); };

    textArea.setAttribute('rows', '3');

    sizeTextField(textArea.id,false);
}

function cloneObject(what) {
    for (i in what) {
        if (typeof what[i] == 'object') {
            this[i] = new cloneObject(what[i]);
        }
        else
            this[i] = what[i];
    }
}

function getTableBefore(at_row, table)
{
    at_row.setAttribute('cuthere', '1');
    tableBefore = table.cloneNode(true);     
    trs = tableBefore.getElementsByTagName('TR');
    while (true)
    {
       if (trs[trs.length-1].getAttribute('cuthere')) {
            trs[trs.length-1].removeAttribute('cuthere');
            trs[trs.length-1].parentNode.removeChild(trs[trs.length-1]);
            break;
       }
       trs[trs.length-1].parentNode.removeChild(trs[trs.length-1]);
    }
    at_row.removeAttribute('cuthere');
    return tableBefore;
}

function getTableAfter(at_row, table)
{
    at_row.setAttribute('cuthere', '1');
    tableAfter = table.cloneNode(true);     
    trs = tableAfter.getElementsByTagName('TR');
    while (true)
    {
       if (trs[0].getAttribute('cuthere')) {
            trs[0].removeAttribute('cuthere');
            trs[0].parentNode.removeChild(trs[0]);
            break;
       }
       trs[0].parentNode.removeChild(trs[0]);
    }
    at_row.removeAttribute('cuthere');
    return tableAfter;
}

function clearSelection () {
    if (navigator.appName == 'Microsoft Internet Explorer') {
        if (document.selection)
            document.selection.empty();
        else if (window.getSelection)
            window.getSelection().removeAllRanges();
    }
}

function inlineEdit(id_start, id_end)
{
    editArea = document.createElement("div");
    editAreaContent = document.getElementById('l' + id_start.toString());

    if (editAreaContent.nodeName == 'TR')
    {
        editArea.setAttribute('class', 'wikitable');
        backupWikiText(id_start, id_end, editAreaContent.parentNode.parentNode.parentNode.innerHTML);
    }
    else
        backupWikiText(id_start, id_end, editAreaContent.innerHTML);

    next_id = getNextId(id_end);

    editAreaContent.ondblclick = '';
    editAreaContentParent = editAreaContent.parentNode;
    if (editAreaContentParent.nodeName == 'SPAN') {
        editAreaContentParent.setAttribute('title', '');
    }
    else if (editAreaContent.nodeName == 'TR') {
        editAreaContent.setAttribute('title', '');
    }

    editAreaContent.className = 'inlineEditHighlight';

    // 2007-4-29 backward compatibility fix
    // should be fixed in directly newer css. 
    editAreaContent.style.overflow = 'hidden';

    if (editAreaContent.nodeName != 'TR') {
        editAreaContentParent.replaceChild(editArea, editAreaContent);
        editArea.appendChild(editAreaContent);
        editAsk = createEditAskArea(id_start, id_end);
        editArea.appendChild(editAsk);
    }
    else {
        // We cut the table in half, creating two tables, and insert the edit area in between them
        table = editAreaContent.parentNode.parentNode;
        original_table_width = table.getElementsByTagName('TR')[0].clientWidth;
        original_table_attributes = table.attributes;
        // record original td widths
        original_td_widths = new Array();
        for (i = 0; i < table.getElementsByTagName('TR')[0].getElementsByTagName('TD').length; i++)
        {
            original_td_widths[i] = table.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i].clientWidth;
        }
        function attachFunction(contentLine, next_id) {
            var contentLine = contentLine;
            return function () { getInlineEditAreas(contentLine, next_id) };
        }
        tableBefore = getTableBefore(editAreaContent, table);
        tableBefore_rows = tableBefore.getElementsByTagName('TR');
        for (i = 0; i < tableBefore_rows.length; i++) {
            tableBefore_rows[i].ondblclick = attachFunction(tableBefore_rows[i], next_id);
        }
        tableAfter = getTableAfter(editAreaContent, table);
        tableAfter_rows = tableAfter.getElementsByTagName('TR');
        for (i = 0; i < tableAfter_rows.length; i++) {
            tableAfter_rows[i].ondblclick = attachFunction(tableAfter_rows[i], next_id);
        }
        if (contentLine) contentLine.ondblclick = attachFunction(contentLine, next_id);
        tableBefore.setAttribute('width', original_table_width.toString() + 'px')
        tableAfter.setAttribute('width', original_table_width.toString() + 'px')

        tableAfterDiv = document.createElement('div');
        tableAfterDiv.setAttribute('class', 'wikitable');
        tableAfterDiv.is_split = 1;
        tableAfterDiv.appendChild(tableAfter);

        tableBeforeDiv = document.createElement('div');
        tableBeforeDiv.setAttribute('class', 'wikitable');
        tableBeforeDiv.is_split = 1;
        tableBeforeDiv.appendChild(tableBefore);

        table.parentNode.replaceChild(tableAfterDiv, table);
        tableAfterDiv.parentNode.insertBefore(tableBeforeDiv, tableAfterDiv);
        tableAfterDiv.parentNode.insertBefore(editArea, tableAfterDiv);
        if (!tableBefore.getElementsByTagName('TR')[0])
            tableBefore.parentNode.removeChild(tableBefore);
        if (!tableAfter.getElementsByTagName('TR')[0])
            tableAfter.parentNode.removeChild(tableAfter);
        editAreaTable = document.createElement("table");
        editAreaTable.setAttribute('width', original_table_width.toString() + 'px');
        for (i = 0; i < original_table_attributes.length; i++)
        {
            editAreaTable.setAttribute(original_table_attributes[i].nodeName, original_table_attributes[i].nodeValue);
        }
        editAreaTable.appendChild(editAreaContent);
        // Set td width to match original table
        for (i = 0; i < original_td_widths.length; i++)
        {
            td_width = original_td_widths[i];
            if (editAreaTable.getElementsByTagName('TR')[0] && editAreaTable.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i])
                editAreaTable.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i].setAttribute('width', td_width);
            if (tableAfter.getElementsByTagName('TR')[0] && tableAfter.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i])
                tableAfter.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i].setAttribute('width', td_width);
            if (tableBefore.getElementsByTagName('TR')[0] && tableBefore.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i])
                tableBefore.getElementsByTagName('TR')[0].getElementsByTagName('TD')[i].setAttribute('width', td_width);
        }
        editArea.appendChild(editAreaTable);

        editAsk = createEditAskArea(id_start, id_end, 'TR');

        editArea.appendChild(editAsk);
    }
    clearSelection();
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
    show("hideMap");
    hide("showMap");
}
function dohide()
{
    hide("map");
    hide("hideMap");
    show("showMap");
}
function doOnLoadStuff()
{
    for (i = 0; i < onLoadStuff.length; i++) {
        eval(onLoadStuff[i]);
    }
    onLoadStuff = new Array();
}
function getElementsByClassName(className, tag, elm){
    var testClass = new RegExp("(^|\\s)" + className + "(\\s|$)");
    var tag = tag || "*";
    var elm = elm || document;
    var elements = (tag == "*" && elm.all)? elm.all : elm.getElementsByTagName(tag);
    var returnElements = [];
    var current;
    var length = elements.length;
    for(var i=0; i<length; i++){
        current = elements[i];
        if(testClass.test(current.className)){
            returnElements.push(current);
        }
    }
    return returnElements;
}
function groupAllRcChanges() {
    rc_entries = getElementsByClassName("rcEntry", "div");
    for (i = 0; i < rc_entries.length; i++) {
        groupChanges(rc_entries[i]);
    }
}
function unGroupChanges(entryNode)
{
    entry = entryNode.parentNode.parentNode;
    mostly_rc_comments = entry.childNodes;
    for (var i = 1; i < (mostly_rc_comments.length-1); i++) {
        if (mostly_rc_comments[i].className == "rccomment") {
            rc_comment = mostly_rc_comments[i];
            rc_comment.style.display = 'block';
        }
    }
    // hide 'show all' node
    entry.removeChild(mostly_rc_comments[mostly_rc_comments.length-1]);
}
function groupChanges(entry)
{
    mostly_rc_comments = entry.childNodes;
    num_comments = 0;
    for (var i = 1; i < mostly_rc_comments.length; i++) {
        if (mostly_rc_comments[i].className == "rccomment") {
            num_comments++;
            if (num_comments > RC_LIST_THRESHOLD) {
                rc_comment = mostly_rc_comments[i];
                parentNode = rc_comment.parentNode;
                rc_comment.style.display = 'none';
            }
        }
    }
    if (num_comments > RC_LIST_THRESHOLD) {
        show_all = document.createElement('div');
        show_all.className = 'rccomment';
        show_all.style.marginTop = ".5em";
        show_all.innerHTML = '&darr;<span onclick="unGroupChanges(this);"><a href="#" onclick="return false;" style="text-decoration:none;">' + (num_comments - RC_LIST_THRESHOLD) + ' more edits</a></span>';
        entry.appendChild(show_all);
    }
}
function createCookie(name,value,seconds) {
    if (seconds) {
        var date = new Date();
        date.setTime(date.getTime()+seconds*1000);
        var expires = "; expires="+date.toGMTString();
    }
    else var expires = "";
    document.cookie = name+"="+value+expires+"; domain="+document.domain+";path=/";
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
    createCookie('can_set_cookies', 'yes', 60*10);
    if(readCookie('can_set_cookies') == 'yes')
    {
        eraseCookie('can_set_cookies');
        return true;
    }
    return false;
}
function authenticateWithFarm()
{
    logout = window.location.href.indexOf('action=userform&logout=Logout');
    if (canSetCookies() && authentication_url && (logout == -1) && !readCookie('nologin'))
    {
        createCookie('nologin', '1', 60*10);
        if (readCookie('nologin') == '1')
            window.location.replace(authentication_url); 
    }
}

authenticateWithFarm();
