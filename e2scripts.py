import os
import sys

def run_script(name, command):
    """
    Executes a shell command and reports the result.

    Args:
        name (str): The descriptive name of the script/command.
        command (str): The shell command string to execute.
    """
    print(f"\n🚀 Starting **{name}** Installation...")
    print(f"Executing command: {command}")
    
    try:
        # Execute the command in the system's shell
        exit_code = os.system(command)
        
        if exit_code == 0:
            print(f"\n✅ **{name}** installation command executed successfully.")
        else:
            # os.system returns the exit status of the command
            print(f"\n⚠️ The **{name}** command returned a non-zero exit code: {exit_code}")
            print("Please check the output above for errors.")
            
    except Exception as e:
        print(f"\n❌ An error occurred during the execution of **{name}**: {e}")

def display_menu(scripts):
    """Displays the interactive menu based on the defined scripts."""
    print("\n" + "="*50)
    print("         🛠️ Enigma2 Script Runner Menu 🛠️         ")
    print("="*50)
    
    # Dynamically print the options from the dictionary
    for key, val in scripts.items():
        # The key is the menu number (e.g., '1'), the value is a dict containing 'name'
        print(f"{key}) Install {val['name']}")
        
    print("q) Quit")
    print("="*50)

def main():
    """Main function to run the script runner application."""
    
    # --- Define all available scripts and their commands ---
    SCRIPTS = {
        '1': {
            'name': 'Eliesat Panel',
            'command': 'wget https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/bash'
        },
        '2': {
            'name': 'Plugload',
            'command': 'wget -q -O - https://github.com/ahmedmoselhi/enigma2-plugins-miscellaneous/raw/refs/heads/master/plugload.sh | /bin/bash'
        },
        '3': {
            'name': 'Mountmanager',
            'command': 'wget -q -O - https://github.com/ahmedmoselhi/enigma2-plugins-miscellaneous/raw/refs/heads/master/mountmanager.sh | /bin/bash'
        },
    }
    # -----------------------------------------------------

    while True:
        display_menu(SCRIPTS)
        
        # Get user input
        choice = input(f"Enter your choice (1-{len(SCRIPTS)} or q): ").strip().lower()

        if choice in SCRIPTS:
            # Get the script details based on the user's choice (e.g., '1')
            script_info = SCRIPTS[choice]
            # Run the script using the dedicated function
            run_script(script_info['name'], script_info['command'])
            
        elif choice == 'q':
            print("👋 Exiting the script runner. Goodbye!")
            sys.exit(0)
            
        else:
            print(f"🚨 Invalid choice. Please enter a number between 1 and {len(SCRIPTS)} or 'q'.")

if __name__ == "__main__":
    # Ensure the script is run directly and not imported
    main()
