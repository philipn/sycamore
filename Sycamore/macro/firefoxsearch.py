from Sycamore import config, wikiutil
from Sycamore.action.Files import getAttachUrl
Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    icon_url = macro.request.getQualifiedURL('/?action=mozilla_search&amp;file=%s.png' % macro.request.config.wiki_name)
    if icon_url:
        icon_link = """<img src="%s"/>&nbsp;""" % icon_url
    else:
        icon_link = ''
    d = { 'src_url': macro.request.getQualifiedURL('/?action=mozilla_search&amp;file=%s.src' % macro.request.config.wiki_name), 
          'sitename': macro.request.config.sitename,
          'wikiname': macro.request.config.wiki_name,
          'icon_url': icon_url,
          'icon_link': icon_link, 
        }

    return formatter.rawHTML("""<script language="JavaScript">
function addEngine(name,cat)
{
    if ((typeof window.sidebar == "object") && (typeof window.sidebar.addSearchEngine == "function"))
    {
        var iconPath = "%(icon_url)s";
        window.sidebar.addSearchEngine("%(src_url)s",iconPath,name,cat );
    }
    else
    {
        alert("The Firefox browser is required to install this plugin.");
    }
}
</script>
<a href="javascript:addEngine(\'%(wikiname)s\',\'Web\')">%(icon_link)sInstall the %(sitename)s search plugin!</a>""" % d)
