#!/usr/bin/perl -I/Users/philipneustrom/sycamore_base_ritual/Sycamore/support/css_cleaner/
# -*-perl-*-
use CSS::Cleaner;

my $cleaner = CSS::Cleaner->new;
$css = '';
while ($line = <STDIN>)
{
    $css = $css . $line;
}

$good = $cleaner->clean($css);
print $good;
