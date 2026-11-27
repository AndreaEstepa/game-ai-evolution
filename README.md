# March of the Pea-Skipper

University project about making a neuroevolutionary model that's able to pogo
over the initial section of Hunter's March in Hollow Knight: Silksong.

## Dependencies

### Silksong

This project uses the video game Hollow Knight: Silksong, by Team Cherry. We do
not own anything related to the game. Its creators own all the rights to the
mentioned game.

### Modloader for Silksong and Used Mods

The [Cogfly](https://github.com/Nix-main/Cogfly) mod manager is used to load
mods into the game. It's subject to the GPLv3 licence.

The [Benchwarp](https://github.com/homothetyhk/Silksong.Benchwarp) mod is used
to set a custom initial spawn point (by deploying a bench). It's subject to the
LGPLv2.1 licence.

The [Snapshot](https://github.com/LingkongSky/Snapshot-SilkSong) mod is used to
set a memory-only save state when starting the process. It's subject to the MIT
licence.

The [No Enemies](https://github.com/T2PeNBiX99wcoxKv3A4g/HKSS.NoEnemies) mod is
used to remove enemies on spawn. It's subject to the MIT licence.

If any of the above mods were to have any dependencies, you should be able to
find more information on their licences in the README files of the mods listed
in here, or similar informative files.

### Robot Environment

For the perception, controlling, and actuating environment, we use the Robot
Operating System ([ROS 2](https://github.com/ros2/ros2)).

Because it's an open-source tool, it's bundled in the container used for the
environment. However, its use is subject to its licence. You can read about it
in the linked repository above.

There are no other requirements than a containerisation tool (Docker, Podman,
etc.) and Xhost for this part. `xhost` is used to allow reading from the
display and showing graphical user interfaces in it.

### Disclaimer

We do not distribute any of the binaries used. However, we store the following
files in the public repository: the vanilla game save, the Benchwarp save
state, and needed configurations to make everything work.

## Building and Running the Environment

1. Create a `.steamuid` file with your Steam user ID inside (just the number).
2. Run `chmod u+x configure && ./configure` to configure the environment.
3. Start Cogfly and import the profile found in `resources/cogfly/profile.r2z`.
4. In the modloader, start Silksong from the imported profile.
5. Once in the game, select the second profile and wait for it to start.
6. Run `xhost +local: && docker compose up` to start the ROS 2 environment and
   wait for the magic to happen.
