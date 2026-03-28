from sys import argv
import os
import json
import hashlib
import getpass
import pickle
import requests
import winshell
import ntpath
import shutil
from win32com.client import Dispatch
from bs4 import BeautifulSoup

# Set these variables to your designed preferences:
add_info_to_output_folder_name = True
add_order_number_to_filename = True
add_source_to_filename = True
allow_approximation_of_invalid_characters = True
allow_input_folder_detection = True
allow_no_arguments = True
allow_search_terms = True
artist_image_filename = "Artist"
back_image_filename = "Back"
create_folder_image = True
create_foobar2000_images = True
create_vgmdb_url_file = True
default_download_to_script_directory = True
disc_image_filename = "Disc"
front_image_filename = "Folder"
pause_at_end = False
process_each_argument_separately = True
show_initial_query = True
output_tab_padding = 4
use_relative_shortcuts = False

first_image_saved = {
    "Front": False,
    "Back": False,
    "Artist": False,
    "Disc": {}
}

import re

scriptdir = os.path.dirname(os.path.abspath(__file__))
config = os.path.join(scriptdir, 'vgmdbrip.pkl')

# Global session variable
session = None

def get_session():
    """Get the current session, initializing if needed."""
    global session
    if session is None:
        session = requests.Session()
    return session

def Soup(data):
    return BeautifulSoup(data, "html.parser")

def get_file_checksum(filepath):
    """Calculate MD5 checksum of a file."""
    if not os.path.exists(filepath):
        return None
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def check_file_exists_in_root(filename_base, extensions=None):
    """Check if a file exists in root directory with any of the given extensions."""
    if extensions is None:
        extensions = ['.jpg', '.png', '.jpeg', '.gif', '.bmp']
    
    for ext in extensions:
        filepath = os.path.join(os.getcwd(), f"{filename_base}{ext}")
        if os.path.exists(filepath):
            return filepath
    
    # Also check for shortcut files that indicate the file exists
    shortcut_filepath = os.path.join(os.getcwd(), f"{filename_base} - Shortcut.lnk")
    if os.path.exists(shortcut_filepath):
        return shortcut_filepath
    
    return None

def check_file_exists_in_subfolder(folder, filename):
    """Check if a file exists in the subfolder."""
    return os.path.exists(os.path.join(folder, filename))

def move_file_and_create_shortcut(source_path, target_path, folder, filename, shortcut_name_override=None):
    """Move a file from source to target and create a shortcut in the subfolder."""
    try:
        # Check if target file already exists
        if os.path.exists(target_path):
            # Check if files are identical using checksum
            source_checksum = get_file_checksum(source_path)
            target_checksum = get_file_checksum(target_path)
            if source_checksum and target_checksum and source_checksum == target_checksum:
                # Files are identical, safe to overwrite - move to root and create shortcut to root
                shutil.move(source_path, target_path)
                shortcut_name = shortcut_name_override or f"{os.path.basename(target_path)} - Shortcut.lnk"
                create_shortcut(target_path, folder, shortcut_name_override=shortcut_name)
                return True
            else:
                # Files are different, don't overwrite - do NOT create shortcut
                print(f"File {os.path.basename(target_path)} already exists and is different. Skipping move and shortcut creation.")
                return False
        else:
            # Target doesn't exist, safe to move
            shutil.move(source_path, target_path)
            # Create shortcut in Scans folder with the scans filename
            shortcut_name = shortcut_name_override or f"{os.path.basename(target_path)} - Shortcut.lnk"
            create_shortcut(target_path, folder, shortcut_name_override=shortcut_name)
            return True
    except Exception as e:
        print(f"Could not move {os.path.basename(source_path)}: {e}")
        return False

def safe_copy_file(source_path, target_path):
    """Safely copy a file without overwriting existing files unless they're identical."""
    try:
        # Check if target file already exists
        if os.path.exists(target_path):
            # Check if files are identical using checksum
            source_checksum = get_file_checksum(source_path)
            target_checksum = get_file_checksum(target_path)
            if source_checksum and target_checksum and source_checksum == target_checksum:
                # Files are identical, safe to overwrite
                shutil.copy2(source_path, target_path)
                return True
            else:
                # Files are different, don't overwrite
                print(f"File {os.path.basename(target_path)} already exists and is different. Skipping copy.")
                return False
        else:
            # Target doesn't exist, safe to copy
            shutil.copy2(source_path, target_path)
            return True
    except Exception as e:
        print(f"Could not copy {os.path.basename(source_path)}: {e}")
        return False

def safe_move_file(source_path, target_path):
    """Safely move a file without overwriting existing files unless they're identical."""
    try:
        # Check if target file already exists
        if os.path.exists(target_path):
            # Check if files are identical using checksum
            source_checksum = get_file_checksum(source_path)
            target_checksum = get_file_checksum(target_path)
            if source_checksum and target_checksum and source_checksum == target_checksum:
                # Files are identical, safe to overwrite
                shutil.move(source_path, target_path)
                return True
            else:
                # Files are different, don't overwrite
                print(f"File {os.path.basename(target_path)} already exists and is different. Skipping move.")
                return False
        else:
            # Target doesn't exist, safe to move
            shutil.move(source_path, target_path)
            return True
    except Exception as e:
        print(f"Could not move {os.path.basename(source_path)}: {e}")
        return False

def get_image_type(filename):
    """Determine image type based on filename patterns."""
    filename_lower = filename.lower()
    
    if any(pattern in filename_lower for pattern in ['front', 'folder']):
        return 'Folder'
    elif 'back' in filename_lower:
        return 'Back'
    elif 'artist' in filename_lower:
        return 'Artist'
    elif 'disc' in filename_lower:
        return 'Disc'
    return None

def get_root_target_filename(filename, image_type, url, disc_num=""):
    """Get the appropriate root target filename for foobar2000 import."""
    # Extract extension from the filename in the subfolder
    if filename and '.' in filename:
        # Get extension from the filename (which includes the URL extension)
        extension = '.' + filename.split('.')[-1]
    else:
        extension = '.jpg'  # Default extension
    
    if image_type == 'Folder':
        return 'Folder.jpg'  # Always use .jpg for Folder image
    elif image_type == 'Back':
        return f'Back{extension}'
    elif image_type == 'Artist':
        return f'Artist{extension}'
    elif image_type == 'Disc':
        if disc_num:
            return f'Disc {disc_num}{extension}'
        else:
            return f'Disc{extension}'
    return None

def scan_subfolder_for_images(folder):
    """Scan subfolder for images and categorize them."""
    images_by_type = {
        'Folder': [],
        'Back': [],
        'Artist': [],
        'Disc': []
    }
    non_shortcut_files = []
    shortcut_count = 0
    
    try:
        for filename in os.listdir(folder):
            # Skip shortcut files entirely - they should never be processed as images
            if filename.endswith('.lnk'):
                shortcut_count += 1
                continue
            
            # Skip URL files (.url extension) as they're not image files
            if filename.endswith('.url'):
                continue
            
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                non_shortcut_files.append(filename)
                image_type = get_image_type(filename)
                if image_type:
                    if image_type == 'Disc':
                        # Extract disc number if present
                        import re
                        disc_match = re.search(r"Disc(?:\s+(\d+))?", filename.split(' - ')[0].strip())
                        disc_num = disc_match.group(1) if disc_match and disc_match.group(1) else ""
                        images_by_type[image_type].append((filename, disc_num))
                    else:
                        images_by_type[image_type].append((filename, ""))
    except OSError:
        pass
    
    # If no Artist images found but there are non-shortcut files, use the first non-shortcut file as Artist
    if not images_by_type['Artist'] and non_shortcut_files:
        # First, check for "Booklet" files (last entry when sorted alphabetically)
        booklet_files = []
        for filename in non_shortcut_files:
            filename_lower = filename.lower()
            if 'booklet' in filename_lower:
                booklet_files.append(filename)
        
        if booklet_files:
            # Sort alphabetically and use the last one
            booklet_files.sort()
            images_by_type['Artist'].append((booklet_files[-1], ""))
        elif shortcut_count >= 3:
            # Look for files that contain Back/Front/etc. but weren't categorized in first pass
            for filename in non_shortcut_files:
                # Check if file contains Back/Front/etc. but wasn't categorized (likely due to different naming)
                filename_lower = filename.lower()
                if any(pattern in filename_lower for pattern in ['back', 'front', 'disc', 'artist']):
                    # This file contains image type keywords but wasn't categorized, use as Artist
                    images_by_type['Artist'].append((filename, ""))
                    break
        else:
            # Find the first file that hasn't been categorized yet
            for filename in non_shortcut_files:
                image_type = get_image_type(filename)
                if not image_type:  # File wasn't categorized as Folder, Back, or Disc
                    images_by_type['Artist'].append((filename, ""))
                    break
    
    return images_by_type

def process_post_download_images(folder, images_by_type):
    """Process images after download phase - move appropriate files to root with checksum validation."""
    for image_type, file_list in images_by_type.items():
        if not file_list:
            continue
            
        if image_type == 'Disc':
            # Process all Disc images
            for filename, disc_num in file_list:
                file_path_subfolder = os.path.join(folder, filename)
                target_filename = get_root_target_filename(filename, image_type, "", disc_num)
                target_path = os.path.join(os.getcwd(), target_filename)
                shortcut_name = f"{filename} - Shortcut.lnk"
                shortcut_path = os.path.join(folder, shortcut_name)
                
                # Check if shortcut already exists - if so, skip processing
                if os.path.exists(shortcut_path):
                    print(f"Shortcut already exists for {filename}, skipping processing.")
                    continue
                
                # Check if target exists and compare checksums
                if os.path.exists(target_path):
                    target_checksum = get_file_checksum(target_path)
                    file_checksum = get_file_checksum(file_path_subfolder)
                    if target_checksum and file_checksum and target_checksum == file_checksum:
                        # Checksums match, move file and create shortcut
                        if move_file_and_create_shortcut(file_path_subfolder, target_path, folder, filename, shortcut_name_override=shortcut_name):
                            print(f"Moved {filename} -> {target_filename} (checksums match)")
                            first_image_saved["Disc"][target_path] = True
                    else:
                        # Different files, don't overwrite - do NOT create shortcut
                        print(f"{target_filename} already exists and is different. Skipping move and shortcut creation.")
                else:
                    # Target doesn't exist, move file and create shortcut
                    if move_file_and_create_shortcut(file_path_subfolder, target_path, folder, filename, shortcut_name_override=shortcut_name):
                        print(f"Moved {filename} -> {target_filename}")
                        first_image_saved["Disc"][target_path] = True
        else:
            # Process first image of each type (Folder, Back, Artist)
            filename, _ = file_list[0]
            file_path_subfolder = os.path.join(folder, filename)
            target_filename = get_root_target_filename(filename, image_type, "")
            target_path = os.path.join(os.getcwd(), target_filename)
            shortcut_name = f"{filename} - Shortcut.lnk"
            shortcut_path = os.path.join(folder, shortcut_name)
            
            # Check if shortcut already exists - if so, skip processing
            if os.path.exists(shortcut_path):
                print(f"Shortcut already exists for {filename}, skipping processing.")
                continue
            
            # Check if target exists and compare checksums
            if os.path.exists(target_path):
                target_checksum = get_file_checksum(target_path)
                file_checksum = get_file_checksum(file_path_subfolder)
                if target_checksum and file_checksum and target_checksum == file_checksum:
                    # Checksums match, move file and create shortcut
                    if move_file_and_create_shortcut(file_path_subfolder, target_path, folder, filename, shortcut_name_override=shortcut_name):
                        print(f"Moved {filename} -> {target_filename} (checksums match)")
                        first_image_saved[image_type] = True
                else:
                    # Different files, don't overwrite - do NOT create shortcut
                    print(f"{target_filename} already exists and is different. Skipping move and shortcut creation.")
            else:
                # Target doesn't exist, move file and create shortcut
                if move_file_and_create_shortcut(file_path_subfolder, target_path, folder, filename, shortcut_name_override=shortcut_name):
                    print(f"Moved {filename} -> {target_filename}")
                    first_image_saved[image_type] = True



def login():
    global session
    if os.path.isfile(config):
        session = pickle.load(open(config, "rb"))
    else:
        while True:
            username = input('VGMdb username:\t')
            password = getpass.getpass('VGMdb password:\t')
            base_url = 'https://vgmdb.net/forums/'
            x = session.post(base_url + 'login.php?do=login', {
            'vb_login_username':        username,
            'vb_login_password':        password,
            'vb_login_md5password':     hashlib.md5(password.encode()).hexdigest(),
            'vb_login_md5password_utf': hashlib.md5(password.encode()).hexdigest(),
            'cookieuser': 1,
            'do': 'login',
            's': '',
            'securitytoken': 'guest'
            })
            table = Soup(x.content).find('table', class_='tborder', width="70%")
            panel = table.find('div', class_='panel')
            message = panel.text.strip()
            print(message)

            if message.startswith('You'):
                if message[223] == '5':
                    raise SystemExit(1)
                print(message)
                continue
            elif message.startswith('Wrong'):
                raise SystemExit(1)
            else:
                break

def print_aligned_columns(arr):
    global output_tab_padding
    
    # Split each row by tabs and transpose the matrix.
    columns = zip(*[row.split('\t') for row in arr])
    
    # Calculate the maximum width for each column.
    max_widths = [max(len(cell) + output_tab_padding - 1 for cell in col) for col in columns]
    
    # Print each row with aligned columns.
    for row in arr:
        cells = row.split('\t')
        formatted_row = ' '.join(f"{cell:{width}}" for cell, width in zip(cells, max_widths))
        print(formatted_row)

def remove(instring, chars):
    for i in range(len(chars)):
        instring = instring.replace(chars[i],"")
    return instring

def strip_special_characters(text):
    """
    Strip special characters from the input text to improve search matching.
    Removes hyphens, underscores, and other special characters that might interfere with search.
    """
    # Remove common special characters that can interfere with search
    special_chars = "-_()[]{}.,!?;:'\"@#$%^&*+=|\\/~`"
    for char in special_chars:
        text = text.replace(char, "")
    return text

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

# Commenting this out to allow prompt approach.
#if(len(argv) < 2):
#    print("usage: " + argv[0] + " vgmdb_album_id")
#    raise SystemExit(1)

# Only call login() when script is run directly, not when imported
if __name__ == "__main__":
    login()
    soup = ""
    if default_download_to_script_directory and os.getcwd() == os.path.dirname(os.path.abspath(__file__)):
        os.chdir(scriptdir)

soup = ""
if default_download_to_script_directory and os.getcwd() == os.path.dirname(os.path.abspath(__file__)):
    os.chdir(scriptdir)

def has_audio_files(directory):
    """Check if directory contains any audio files."""
    audio_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma', '.ape', '.wv', '.tta', '.mp4', '.m4b', '.m4p', '.m4v', '.mpc', '.mp2', '.mp1', '.ac3', '.dts', '.opus', '.webm', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.3g2', '.m2ts', '.mts', '.ts', '.vob', '.ifo', '.divx', '.xvid', '.rm', '.rmvb', '.asf', '.mka', '.mks', '.ogv', '.m3u', '.m3u8', '.pls', '.cue', '.wpl', '.xspf', '.asx', '.wax', '.wvx', '.m3u', '.m3u8', '.pls', '.cue', '.wpl', '.xspf', '.asx', '.wax', '.wvx'}
    
    try:
        for filename in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, filename)):
                if os.path.splitext(filename)[1].lower() in audio_extensions:
                    return True
    except OSError:
        pass
    return False

def has_disc_cd_subfolders(directory):
    """Check if directory has subfolders with Disc/CD patterns."""
    import re
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                # Check for Disc X, CD X, or CDX patterns (case insensitive)
                if re.search(r'(disc\s*\d+|cd\s*\d+|cd\d+)', item, re.IGNORECASE):
                    return True
    except OSError:
        pass
    return False

def process_disc_cd_subfolders(directory):
    """Process each Disc/CD subfolder as a separate script call."""
    import re
    import subprocess
    import sys
    
    subfolders = []
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                # Check for Disc X, CD X, or CDX patterns (case insensitive)
                if re.search(r'(disc\s*\d+|cd\s*\d+|cd\d+)', item, re.IGNORECASE):
                    subfolders.append(item_path)
    except OSError:
        pass
    
    # Sort subfolders to process in consistent order
    subfolders.sort()
    
    for subfolder in subfolders:
        print(f"\nProcessing subfolder: {os.path.basename(subfolder)}")
        print(f"Changing to directory: {subfolder}")
        os.chdir(subfolder)
        # Call the script recursively for this subfolder
        # We'll use the current script file path and pass the subfolder as argument
        script_path = os.path.abspath(__file__)
        try:
            # Use subprocess to call the script with the subfolder as argument
            subprocess.run([sys.executable, script_path, subfolder], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing {subfolder}: {e}")
        except Exception as e:
            print(f"Unexpected error processing {subfolder}: {e}")

def process_immediate_subfolders(directory):
    """Process each immediate subfolder as a separate script call."""
    import subprocess
    import sys
    
    subfolders = []
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                subfolders.append(item_path)
    except OSError:
        pass
    
    # Sort subfolders to process in consistent order
    subfolders.sort()
    
    # Check if any subfolder contains audio files
    has_audio_in_subfolders = False
    for subfolder in subfolders:
        if has_audio_files(subfolder):
            has_audio_in_subfolders = True
            break
    
    if has_audio_in_subfolders:
        # Process only subfolders that contain audio files
        for subfolder in subfolders:
            if has_audio_files(subfolder):
                print(f"\nProcessing subfolder: {os.path.basename(subfolder)}")
                print(f"Changing to directory: {subfolder}")
                os.chdir(subfolder)
                # Call the script recursively for this subfolder
                script_path = os.path.abspath(__file__)
                try:
                    # Use subprocess to call the script with the subfolder as argument
                    subprocess.run([sys.executable, script_path, subfolder], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error processing {subfolder}: {e}")
                except Exception as e:
                    print(f"Unexpected error processing {subfolder}: {e}")
    else:
        # No subfolders contain audio files, process the original directory
        print(f"No audio files found in any subfolders of '{directory}'. Processing original directory.")
        return False  # Return False to indicate we should process the original path
    
    return True  # Return True to indicate we processed subfolders

def download_vgmdb_art(query):
    ids = []
    choice_index = 0
    album_url = None  # Store the final album URL
    
    # If allow_input_folder_detection is enabled and query is to a file or folder that exists:
    if allow_input_folder_detection and os.path.exists(query):
        if os.path.isfile(query):
            # Change to the folder path.
            os.chdir(os.path.dirname(query))
            # Get the folder name.
            query = os.path.basename(os.path.dirname(query))
        else:
            # Check if the directory contains audio files
            if not has_audio_files(query):
                # Directory doesn't contain audio files, check for Disc/CD subfolders
                if has_disc_cd_subfolders(query):
                    print(f"Directory '{query}' doesn't contain audio files, but has Disc/CD subfolders. Processing each subfolder separately.")
                    process_disc_cd_subfolders(query)
                    return  # Exit after processing subfolders
                else:
                    # No Disc/CD subfolders, try processing immediate subfolders
                    print(f"Directory '{query}' doesn't contain audio files and has no Disc/CD subfolders. Checking immediate subfolders.")
                    if process_immediate_subfolders(query):
                        return  # Exit after processing subfolders
            
            os.chdir(query)
            # Get the folder name.
            query = os.path.basename(query)
        # If the folder name contains spaces:
        if " " in query:
            # Remove hyphens so that terms aren't excluded.
            query = query.replace("-", "")
    
    if show_initial_query:
        print('Query: ' + query)
    
    # Handle existing files from older versions that didn't have shortcut functionality
    folder = "Scans (VGMdb)"
    if add_info_to_output_folder_name and len(ids) > 0:
        if len(media_formats) == len(ids): folder += f" ({media_formats[choice_index]})"
        if len(catalogs) == len(ids) and catalogs[choice_index] != "N/A": folder += f" [{catalogs[choice_index]}]"
        folder = get_valid_windows_name(folder, allow_approximation_of_invalid_characters)
    
    # Check for existing files that need to be moved/updated
    if os.path.exists(folder):
        # Check if folder.jpg exists in root and matches front image in subfolder
        root_front_paths = [os.path.join(os.getcwd(), "Folder.jpg"), os.path.join(os.getcwd(), "folder.jpg")]
        # Look for the first scan image (front image) in the subfolder - check for any extension
        front_path = None
        try:
            for item in os.listdir(folder):
                if item.startswith("01 Front"):
                    front_path = os.path.join(folder, item)
                    break
        except OSError:
            pass
        
        for root_front_path in root_front_paths:
            if os.path.exists(root_front_path) and front_path and os.path.exists(front_path):
                root_checksum = get_file_checksum(root_front_path)
                front_checksum = get_file_checksum(front_path)
                if root_checksum and front_checksum and root_checksum == front_checksum:
                    try:
                        # Use safe move operation for front image
                        target_front_path = os.path.join(os.getcwd(), "Folder.jpg")
                        if safe_move_file(front_path, target_front_path):
                            # Create shortcut in VGMdb folder pointing to the moved file
                            shortcut_name = f"{os.path.basename(target_front_path)} - Shortcut.lnk"
                            shortcut_path = os.path.join(folder, shortcut_name)
                            create_shortcut(target_front_path, folder, shortcut_name_override=shortcut_name)
                            first_image_saved["Front"] = True
                    except Exception as e:
                        print(f"Could not move front image: {e}")




        
        # Move existing files from subfolder to root and create shortcuts
        files_to_move = {
            "Back": back_image_filename,
            "Artist": artist_image_filename
        }
        
        for file_type, base_filename in files_to_move.items():
            target_filename = f"{base_filename}.jpg"
            target_path = os.path.join(os.getcwd(), target_filename)
            source_path = os.path.join(folder, target_filename)
            shortcut_name = f"{target_filename} - Shortcut.lnk"
            shortcut_path = os.path.join(folder, shortcut_name)
            
            if os.path.exists(source_path) and not os.path.exists(target_path) and not os.path.exists(shortcut_path):
                try:
                    # Use safe move operation
                    if safe_move_file(source_path, target_path):
                        # Create shortcut in VGMdb folder
                        create_shortcut(target_path, folder, shortcut_name_override=shortcut_name)
                        first_image_saved[file_type] = True
                except Exception as e:
                    print(f"Could not move {target_filename}: {e}")
        
        # Handle disc files
        disc_files = []
        try:
            for item in os.listdir(folder):
                if re.search(r"Disc(\s+\d+)?", item.split(' - ')[0].strip()):
                    disc_files.append(item)
        except OSError:
            pass
        
        for disc_file in disc_files:
            disc_path = os.path.join(folder, disc_file)
            # Extract disc number if present
            disc_match = re.search(r"Disc(?:\s+(\d+))?", disc_file.split(' - ')[0].strip())
            disc_num = disc_match.group(1) if disc_match and disc_match.group(1) else ""
            
            if disc_num:
                target_filename = f"{disc_image_filename} {disc_num}.jpg"
            else:
                target_filename = f"{disc_image_filename}.jpg"
            
            target_path = os.path.join(os.getcwd(), target_filename)
            shortcut_name = f"{disc_file} - Shortcut.lnk"
            shortcut_path = os.path.join(folder, shortcut_name)
            disc_key = target_filename
            
            if os.path.exists(disc_path) and not os.path.exists(target_path) and not os.path.exists(shortcut_path):
                try:
                    # Use safe move operation
                    if safe_move_file(disc_path, target_path):
                        # Create shortcut in VGMdb folder
                        create_shortcut(target_path, folder, shortcut_name_override=shortcut_name)
                        first_image_saved["Disc"][disc_key] = True
                except Exception as e:
                    print(f"Could not move {disc_file}: {e}")


    
    while True:
        #print('Query: ' + query)
        query = query.replace("https://vgmdb.net/album/", "")
        if(query.isdigit()):
            soup = Soup(session.get("https://vgmdb.net/album/" + query).content)
            break
        
        if allow_search_terms:
            soup = Soup(session.get("https://vgmdb.net/search?q=" + query).content)
        else:
            soup = Soup(session.get("https://vgmdb.net/search?q=\"" + query + "\"").content)
            
        if(soup.title.text[:6] != "Search"):
            break
        else:
            if not allow_search_terms:
                print("stuck at search results")
                exit(1)
            
            soupHTML = str(soup)
            #print(soupHTML)
            
            # Get all matches and split them into separate lines
            #import re
            ids = re.findall(r'href="http://vgmdb.net/album/(\d+)"\s+title="[^"]+"', soupHTML)
            catalogs = re.findall(r'span class="catalog[^"]*">([^<]+)</span>', soupHTML)
            album_titles = re.findall(r'href="http://vgmdb.net/album/\d+"\s+title="([^"]+)"', soupHTML)
            release_dates = re.findall(r'"View albums released on ([^"]+)', soupHTML)
            release_dates += re.findall(r'text-align: right[^>]+>(\d\d\d\d)<', soupHTML)
            media_formats = re.findall(r'text-align: right[^>]+>([^<>\r\n]+[^<>\r\n\d])<', soupHTML)
            
            if len(ids) > 0:
                # Separate reprints from non-reprints and sort them
                non_reprints = []
                reprints = []
                
                for i, (title, catalog, media_format) in enumerate(zip(album_titles, catalogs, media_formats)):
                    # Check if this is a reprint (child album) by looking for the child album icon in the HTML
                    # Look for the specific pattern that indicates a child album/reprint
                    # The child album icon appears in the same row as the album link
                    album_id = ids[i]
                    # Look for the row containing this album ID and check if it has the child album icon
                    # Use a more precise pattern that captures only the specific row
                    # The pattern looks for <tr> tag, then any content until the album link, then stops at the next </tr>
                    album_row_pattern = rf'<tr[^>]*>.*?href="http://vgmdb.net/album/{album_id}"[^>]*>.*?</tr>'
                    album_row_match = re.search(album_row_pattern, soupHTML, re.IGNORECASE)
                    
                    is_reprint = False
                    if album_row_match:
                        album_row = album_row_match.group(0)
                        # Check if this row contains the child album icon
                        # Look specifically for the child album icon pattern within this row
                        if re.search(r'album-reprint\.gif', album_row, re.IGNORECASE):
                            is_reprint = True
                    
                    title_with_label = f"{title} [Reprint]" if is_reprint else title
                    
                    album_info = {
                        'index': i,
                        'title': title_with_label,
                        'catalog': catalog,
                        'media_format': media_format,
                        'is_reprint': is_reprint
                    }
                    
                    if is_reprint:
                        reprints.append(album_info)
                    else:
                        non_reprints.append(album_info)
                
                # Combine lists with non-reprints first, then reprints
                sorted_albums = non_reprints + reprints
                
                # Display search results for user selection
                print("Multiple results found:")
                for i, album in enumerate(sorted_albums):
                    print(f"{i+1}. {album['title']} ({album['catalog']}, {album['media_format']})")
                
                # Allow user to select a result or enter new search
                while True:
                    choice = input("Enter the number of the album to download, or enter a new search query: ")
                    try:
                        # Try to parse as a number first
                        choice_index = int(choice) - 1
                        if 0 <= choice_index < len(ids):
                            # Get the original index from the sorted list
                            original_index = sorted_albums[choice_index]['index']
                            query = ids[original_index]
                            print(f"Selected: {sorted_albums[choice_index]['title']}")
                            break
                        else:
                            print("Invalid choice. Please enter a number from 1 to " + str(len(ids)) + " or a new search query.")
                    except ValueError:
                        # If not a number, treat as new search query
                        query = choice
                        if show_initial_query:
                            print('Query: ' + query)
                        break
            else:
                print("No search results found.")
                # Prompt for new input and restart the loop
                query = input("Enter the VGMdb URL ID or search query for which you want to download album art: ")
                if show_initial_query:
                    print('Query: ' + query)
                continue
    
    print('Title: ' + soup.title.text)

    folder = "Scans (VGMdb)"
    if add_info_to_output_folder_name and len(ids) > 0:
        if len(media_formats) == len(ids): folder += f" ({media_formats[choice_index]})"
        if len(catalogs) == len(ids) and catalogs[choice_index] != "N/A": folder += f" [{catalogs[choice_index]}]"
        folder = get_valid_windows_name(folder, allow_approximation_of_invalid_characters)


    # Create .url file pointing to VGMDb album page in the scans folder
    if create_vgmdb_url_file:
        # Use the current URL from the soup object
        current_url = soup.find('link', rel='canonical')
        if current_url:
            album_url = current_url.get('href')
        else:
            # Fallback to constructing URL from the title or using a default pattern
            album_url = f"https://vgmdb.net/album/{query}"
        
        url_filename = f"{get_valid_windows_name(soup.title.text, allow_approximation_of_invalid_characters)}.url"
        ensure_dir(folder + os.sep)
        url_filepath = os.path.join(folder, url_filename)
        if not os.path.exists(url_filepath):
            with open(url_filepath, 'w') as f:
                f.write(f"[InternetShortcut]\nURL={album_url}\n")
            print(f"Created VGMDb URL shortcut: {url_filepath}")
        else:
            print(f"VGMDb URL shortcut already exists, skipping")

    gallery = soup.find("div", attrs={"class" : "covertab", "id" : "cover_gallery"})

    if gallery is None:
        print("No album art gallery found on VGMdb page")
        return

    # Phase 1: Download all images to subfolder without special processing
    for idx, scan in enumerate(gallery.find_all("a", attrs={"class": "highslide"}), start=1):
        url = scan["href"]
        title = get_valid_windows_name(scan.text, allow_approximation_of_invalid_characters)
        ensure_dir(folder + os.sep)
        order_number = str(idx).zfill(2)
        source_filename_with_extension = os.path.splitext(os.path.basename(url))[0]
        filename = ""
        if add_order_number_to_filename:
            filename += f"{order_number} "
        filename += title
        if add_source_to_filename:
            filename += f" [{source_filename_with_extension}]"
        filename += url[-4:]

        # Check if file already exists before downloading
        file_path = os.path.join(folder, filename)
        shortcut_path = os.path.join(folder, f"{filename} - Shortcut.lnk")
        if os.path.exists(file_path) or os.path.exists(shortcut_path):
            print(f"{filename} already exists, skipping")
            continue

        # Download the image
        image = session.get(url).content
        
        # Write the image to file
        with open(file_path, "wb") as f:
            f.write(image)
        print(f"{filename} downloaded.")

    # Phase 2: Process images for foobar2000 compatibility
    if create_foobar2000_images:
        print("\nProcessing images for foobar2000 compatibility...")
        images_by_type = scan_subfolder_for_images(folder)
        process_post_download_images(folder, images_by_type)

        
        
    pickle.dump(session, open(config, "wb"))


def create_shortcut(shortcut_target, shortcut_path="", shortcut_windows_style=True, shortcut_name_override=None):
    """
    Create a shortcut to the target file/folder (relative or absolute based on config).
    """
    global use_relative_shortcuts

    # Determine shortcut name
    if shortcut_name_override:
        shortcut_name = shortcut_name_override
    else:
        shortcut_name = get_name_with_extension(shortcut_target)
        if get_file_extension(shortcut_name) != '.lnk':
            if shortcut_windows_style:
                shortcut_name = f"{shortcut_name} - Shortcut"
            shortcut_name = f"{shortcut_name}.lnk"

    # Determine shortcut filepath - place in the specified path
    shortcut_filepath = os.path.join(shortcut_path, shortcut_name)

    # Get absolute path of target
    target_abs = os.path.abspath(shortcut_target)

    # Create the shortcut
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortcut(shortcut_filepath)

    if use_relative_shortcuts:
        # Use relative method
        shortcut_dir = os.path.dirname(shortcut_filepath)
        try:
            relative_path = os.path.relpath(target_abs, shortcut_dir)
        except ValueError:
            print(f"Cannot create relative path for {shortcut_target}")
            return

        shortcut.TargetPath = r'%windir%\explorer.exe'
        shortcut.Arguments = f'"{relative_path}"'
        shortcut.WorkingDirectory = ''
        shortcut_type = "Relative"
    else:
        # Use absolute method
        shortcut.TargetPath = target_abs
        shortcut.Arguments = ''
        shortcut.WorkingDirectory = os.path.dirname(target_abs)
        shortcut_type = "Absolute"

    # Don't set IconLocation to allow Windows auto-detection (like native shortcuts)
    shortcut.Save()

    print(f"{shortcut_type} shortcut created: {shortcut_filepath}")

def download_image(url, save_path = ""):
    # If save_path is to a folder or save_path doesn't have an extension, set filepath based on URL.
    if os.path.isdir(save_path) or not has_file_extension(save_path):
        file_name_with_extension = get_name_with_extension(url)
        save_path = os.path.join(save_path, file_name_with_extension)

    if not os.path.exists(save_path):
        response = session.get(url)
        image = response.content

        with open(save_path, "wb") as f:
            f.write(image)

        # Try to get modification time from VGMdb cover page
        cover_id = os.path.splitext(os.path.basename(url))[0]
        if cover_id.isdigit():
            try:
                cover_url = f"https://vgmdb.net/db/covers.php?do=view&cover={cover_id}"
                cover_response = session.get(cover_url)
                cover_soup = Soup(cover_response.content)
                # Find the added date
                smallfont_div = cover_soup.find('div', class_='smallfont')
                if smallfont_div and 'added on' in smallfont_div.text:
                    date_text = smallfont_div.text
                    # Parse "added on Apr 23, 2010 06:11 PM"
                    import re
                    date_match = re.search(r'added on (\w+ \d+, \d{4}) .*?(\d+:\d+ (?:AM|PM))', date_text)
                    if date_match:
                        date_str = f"{date_match.group(1)} {date_match.group(2)}"
                        from datetime import datetime
                        mtime = datetime.strptime(date_str, '%b %d, %Y %I:%M %p').timestamp()
                        os.utime(save_path, (mtime, mtime))
            except Exception:
                # Fallback to Last-Modified header
                if 'Last-Modified' in response.headers:
                    try:
                        from email.utils import parsedate_to_datetime
                        mtime = parsedate_to_datetime(response.headers['Last-Modified']).timestamp()
                        os.utime(save_path, (mtime, mtime))
                    except Exception:
                        pass  # Ignore parsing errors

        print(f"{os.path.basename(save_path)} downloaded.")
    else:
        print(f"{os.path.basename(save_path)} already exists, skipping download.")

# Return just the file extension of the given path (including the dot).
def get_file_extension(path):
    # If path is to a folder that exists, return an empty string.
    if os.path.isdir(path):
        return ''
    else:
        return os.path.splitext(path)[1]

# Return just the file or folder name of the given path.
def get_name_with_extension(path):
	return ntpath.basename(path)

def get_valid_windows_name(filename, approximation):
    """
    Replaces forbidden characters in filename.
    Args:
        filename (str): The input text to process.
        approximation (bool): Whether to replace illegal characters using unusual characters that approximate them.
    Returns:
        str: The processed text with forbidden characters replaced.
    """
    
    # Strip leading and trailing whitespace from the filename.
    filename = filename.strip()
    
    if not approximation:
        filename = remove(filename, "\"*/:<>?\\|")
    else:        
        # Define a dictionary of filename bad characters and their replacements.
        replacements = {
            '"': '“',
            '>': '＞',
            '<': '＜',
            '?': '？',
            ':': '：',
            '*': '✱',
            '|': '│',
            '\\': '＼',
            '/': '／'
        }
        
        # Replace all bad characters with their equivalent replacements.
        for char in replacements:
            filename = filename.replace(char, replacements[char])
    
    return filename

def has_file_extension(path):
    _, extension = os.path.splitext(path)
    return bool(extension)

if __name__ == "__main__":
    if len(argv) < 2:
        if allow_no_arguments:
            download_vgmdb_art(input("Enter the VGMdb URL ID or search query for which you want to download album art: "))
        else:
            print("usage: " + argv[0] + " vgmdb_album_id")
            raise SystemExit(1)
    else:
        if process_each_argument_separately:
            for arg in argv[1:]:
                download_vgmdb_art(f"{arg}")
        else:
            download_vgmdb_art(" ".join(argv[1:]))

    if pause_at_end:
        input("Press Enter to exit...")
