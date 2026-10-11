# Reverse_Interlinear
To use alongside your bible reading: Reverse Interlinear script to map KJV and sometimes ESV and others potentially to their STRONG'S numbers

# What
- A completely offline reverse interlinear you "make" using this install script. Even the fonts are offline (fonts not yet tested).

# Who made it

- AI. So blame AI if it doesn't work.
- I spent about zero minutes on this. It seems to work fine and use the below data sets. That's fine for now.

# Why 
- For the apocalypse, silly.
- If they shut off the lights, you will want to go to your linux box command line and type in "interlinear.py john 1:1". No e-sword required, no online access required, just simple mapping.

# Stuff I asked it to use
- Thayers for Greek, BDB for Hebrew, possibly to consult the NETS Septuagint although I may have forgotten to specify the flavor.


# Installation

This is a command-line-only tool. No GUI is required.

1. Create a working directory

Create a directory to hold the required repositories and the interlinear.py script. The directory name is up to you.

mkdir interlinear_tool
cd interlinear_tool

2. Clone the required repositories

Run the following commands from inside your working directory:

git clone https://github.com/STEPBible/STEPBible-Data.git
git clone https://github.com/openscriptures/strongs.git
git clone https://github.com/crizin/bible-db.git
git clone https://gitlab.com/crosswire-bible-society/kjv.git kjv-strongs


Note: You only need to do this once. Repeat these commands only if you want to update the source repositories. The repositories provide the source data that the tool uses locally.

3. Set up the script

Place interlinear.py in your working directory, alongside the cloned repositories.

Run the script:

python3 interlinear.py


Make it executable:

chmod +x interlinear.py


The script handles setup, indexing, and standalone SQLite database creation as needed.

4. Run the tool

You're ready to go!

The following examples demonstrate how to use the tool:

# Verify that all required source files were found
./interlinear.py --sources

# Look up a verse (the first run builds the index)
./interlinear.py 1 john 1:1

# Look up a verse in Sirach
./interlinear.py sirach 1:1

# Look up John 3:16, showing all versions with full output
./interlinear.py john 3:16 -V ALL --full

# Display help
./interlinear.py -h


First-run note: The first lookup builds the index. This typically takes about 30 seconds and uses approximately 250 MB of disk space in ~/.cache. Subsequent lookups reuse the index.

Once the index is built, you generally won't need to repeat the setup unless you want to update the source repositories or rebuild the index.

# Install foregn language fonts (OPTIONAL)
- See text file in this package

keywords: bible, interlinear, lookup, look-up, mapping, verses, commandline, command line, offline


