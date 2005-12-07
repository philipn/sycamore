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
	if ($wiki =~ s/attachment:(.*?)([\s|])/smurfette0/s) {
		$foo = $1;  $bar = $2;  }
	$foo = `python fiximagename.py $foo`;
	chop($foo);
	$wiki =~ s/smurfette0/[[Image($foo)]]$bar/s;
}

while ($wiki =~ /borderless:/s  ) {
	if ($wiki =~ s/borderless:(.*?)([\s|])/smurfette0/s) {
		$foo = $1;  $bar = $2;  }
	$foo = `python fiximagename.py $foo`;
	chop($foo);
	$wiki =~ s/smurfette0/[[Image($foo, noborder)]]$bar/s;
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
	$imagefile = `python fiximagename.py $thumbarg[0]`;
	chop($imagefile);
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
 #	print $imagestring; 
	# insert new image tag
	$wiki =~ s/smurfsmurf/$imagestring/;
}


#replace comments
while ($wiki =~ /smurf\d/) {
	$wiki =~ s/smurf(\d+)/$comments[$1]/s;
}



open(WIKIOUT, ">", $fileout) or die "Can't open output: $fileout\n";
print WIKIOUT $wiki;
close WIKIOUT;

print "exit success\n";


