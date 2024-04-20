# Sailing Era Trading Route Calculator

This Python script implements the methodology described by [Jathby Dredas's guide on Steam](https://steamcommunity.com/sharedfiles/filedetails/?id=2983784638).

![Sample Output](https://i.imgur.com/RQJsnei.png "Sailing Era Trade Routes calculator sample output")

Using the same data sets, the script generates and evaluates all possible trade routes in the game Sailing Era. The script can output the top trade routes globally, or the best trade routes for any specific port for cities you've already established guilds in, and can either run local trades (only 1 month away) or long range trades if you have a Charting Office.

(Also, you don't have to worry about "depleting the supply", even unguilded ports have unlimited quantities of trade goods available to trade fleets, I've tested this hypothesis rigorously.)

## Instructions (For the Complete Newbie)

1. **Install Python**
   - Download and install Python. Ensure you configure your environment variables during installation to use Python from the command line.

2. **Install Required Packages**
   - Open your command line interface and install the necessary Python packages:

```bash
pip install pandas
pip install fuzzywuzzy
pip install python-levenshtein
```

3. Clone this Repository

Check out this repo and save it to a local folder.

4. Run the script!

Open a command line in this directory (if you're in Win10 or Win11, type "cmd" into the address bar and it will pull right up) and run the following command: "python main.py"

## Additional Notes:

If the game ever comes out with some updates and I haven't updated this github, you can:
- modify the .csv files with the appropriate data
- delete global_trade_routes.zip
- rerun the script

Lacking the global_trade_routes file, the script will regenerate it.

Additionally, you can ignore region_time_data.py (which I used to generate the region_travel_matrix.csv based on the graphic that Jathby Dredas posted in his guide), and you can ignore wiki_data.py and the correspoding cache directory, which I used to scrape data from the Sailing Era wiki.