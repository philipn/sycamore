import re, string
from Sycamore import config

Dependencies = []

def getArguments(args, request):
    split_args = args.split(',')
    paypal_address = split_args[0]
    if len(split_args) == 2:
        cobrand = split_args[1]
    else:
        cobrand = config.sitename
    return (paypal_address, cobrand)
    
   
def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    if not args:
        return formatter.rawHTML('<form action="https://www.paypal.com/cgi-bin/webscr" method="post"> <input type="hidden" name="cmd" value="_xclick"> <input type="hidden" name="business" value="'+ config.paypal_address +'"> <input type="hidden" name="item_name" value="'+ config.sitename +'"> <input type="hidden" name="item_number" value="1"> <input type="hidden" name="no_note" value="1"> <input type="hidden" name="currency_code" value="USD"> <input type="hidden" name="tax" value="0"> <input type="image" src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" border="0" name="submit" alt="Make payments with PayPal - it\'s fast, free and secure!"> </form>')     
    if args:
        paypal_address, cobrand = getArguments(args, macro.request)
                        
        if re.match("^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,3})$", paypal_address) != None:
            return formatter.rawHTML('<form action="https://www.paypal.com/cgi-bin/webscr" method="post"> <input type="hidden" name="cmd" value="_xclick"> <input type="hidden" name="business" value="'+ paypal_address +'"> <input type="hidden" name="item_name" value="'+ cobrand +'"> <input type="hidden" name="item_number" value="1"> <input type="hidden" name="no_note" value="1"> <input type="hidden" name="currency_code" value="USD"> <input type="hidden" name="tax" value="0"> <input type="image" src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" border="0" name="submit" alt="Make payments with PayPal - it\'s fast, free and secure!"> </form>')
        else:
            return formatter.rawHTML('<strong>The Email address you specified seems malformed: ' + paypal_address + '</strong>')

