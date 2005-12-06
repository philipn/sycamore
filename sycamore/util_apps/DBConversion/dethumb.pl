#!/usr/bin/perl

# dethumb.pl
# syntax:  perl dethumb.pl [input file] [output file]

use warnings;
$/ = undef;

defined($ARGV[0]) or die "syntax:  perl dethumb.pl [input file] [output file]\n";

$filein = $ARGV[0];
$fileout = $ARGV[1];

open(WIKIPAGE, "<", $filein) or die "Can't open input: $filein\n";

$wiki = <WIKIPAGE>;

close WIKIPAGE;


@comments = undef;
$i = 0;

while ($wiki =~ /\{\{\{.*?\}\}\}/s) {
        if ( $wiki =~ s/(\{\{\{.*?\}\}\})/smurf$i/s) {
                $comments[$i] = $1;
        }
        $i++;
}


while ($wiki =~ /attachment:/s  ) {
        $wiki =~ s/attachment:(\w+?\.\w\w\w\w?)(\W)/[[Image($1)]]$2/s;
}

while ($wiki =~ /borderless:/s  ) {
        $wiki =~ s/borderless:(\w+?\.\w\w\w\w?)(\W)/[[Image($1, noborder)]]$2/s;
}




# thumbnails!
while($wiki =~ /\[\[Thumbnail/    ) {
        if ($wiki =~ s/\[\[Thumbnail\((.+?)\)\]\]/smurfsmurf/ ) {
                $thumbargs = $1;
        }
        $caption = undef;
        # get caption, if exists
        if ($thumbargs =~ /".*"/) {
                if ($thumbargs =~ s/,\s*"(.*)"//) {
                        $caption = $1;
                }
        }
        #clear whitespace
        $thumbargs =~ s/\s//g;
        @thumbarg = undef;
        # get remaining arguments
        @thumbarg = split /,/, $thumbargs;
        $imagefile = $thumbarg[0];
        $imagesize = $leftitude = undef;
        for($k=1; $k <= $#thumbarg; $k++) {
                $thumbarg[$k] =~ /\d/ and $imagesize = $thumbarg[$k];
                $thumbarg[$k] =~ /left/ and $leftitude = $thumbarg[$k];
                $thumbarg[$k] =~ /right/ and $leftitude = $thumbarg[$k];
        }
        $imagestring = '[[Image(' . $imagefile;
        defined($caption) and   $imagestring = $imagestring . ', "' . $caption . '"';
        defined($imagesize) and $imagestring = $imagestring . ', ' . $imagesize;
        defined($leftitude) and  $imagestring = $imagestring . ', ' . $leftitude;
        
        $imagestring = $imagestring . ', ' . 'thumbnail)]]';
 #      print $imagestring; 
        # insert new image tag
        $wiki =~ s/smurfsmurf/$imagestring/;
}


while ($wiki =~ /smurf\d/) {
        $wiki =~ s/smurf(\d+)/$comments[$1]/s;
}



open(WIKIOUT, ">", $fileout) or die "Can't open output: $fileout\n";
print WIKIOUT $wiki;
close WIKIOUT;

print "exit success\n";
