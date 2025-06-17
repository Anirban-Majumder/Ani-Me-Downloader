import pickle, re

load_res = []  # list[[name, magnet, size], ...]
with open('result.pkl', 'rb') as f:
    load_res = pickle.load(f)

name = "SAKAMOTO DAYS"
search_name = "SAKAMOTO DAYS"
res = "1080p"
compressed = True  # 265 / 264 / hvec in name
episode_number = 5

def find_best_match(items, name, search_name, res, compressed, episode_number):
    # Precompute lowercase search strings
    name_lower = name.lower()
    search_name_lower = search_name.lower()
    res_lower = res.lower()
    
    # Set compression patterns and compile regex patterns ahead
    comp_patterns = ["265", "264", "hevc", "avc"] if compressed else []

    
    for title, magnet, size in items:
        title_lower = title.lower()
        # Quick filter by resolution and name match
        if res_lower in title_lower and (name_lower in title_lower or search_name_lower in title_lower):
            if not compressed or any(c in title_lower for c in comp_patterns):
                # Check for matching release groups and episode patterns
                    if '[ember]' in title_lower:
                        additional = f' s{self.season:02}e{episode_number:02} '
                        if additional in title_lower:
                            return magnet
                    elif '[subsplease]' in title_lower:
                        additional = f'{" s " + str(self.season) if self.season >= 2 else ""} - {episode_number:02} '
                        if additional in title_lower:
                            return magnet
                    elif '[erai-raws]' in title_lower:
                        additional = f'{episode_number:02} '
                        if additional in title_lower:
                            return magnet
                    elif '[toonshub]' in title_lower:
                        additional = f'e{episode_number} '
                        if additional in title_lower:
                            return magnet
                    else:
                        additional = f' s{self.season:02}e{episode_number:02} ' if self.season >= 2 else f' e{episode_number:02} '
                        if additional in title_lower:
                            return magnet
                        additional = f' s{self.season:02}e{episode_number:02} '
                        if additional in title_lower:
                            return magnet

                    
    return None


best_match = find_best_match(load_res, name, search_name, res, compressed, episode_number)
if best_match:
    title, magnet, size = best_match
    print(f"Found match: {title}")
    print(f"Magnet: {magnet}")
    print(f"Size: {size}")
else:
    print("No matching item found")

#take in  consderation mib and gib in size
#print smallest
def find_smallest(items):
    min_size = float('inf')
    min_item = None
    for title, magnet, size in items:
        size_num = float(size.split(" ")[0])
        if size.endswith("GiB") or size.endswith("G"):
            size_num *= 1024
        if size_num < min_size:
            min_size = size_num
            min_item = title, magnet, size
    return min_item

smallest = find_smallest(load_res)
if smallest:
    title, magnet, size = smallest
    print(f"Smallest item: {title}")
    print(f"Magnet: {magnet}")
    print(f"Size: {size}")
else:
    print("No items found")