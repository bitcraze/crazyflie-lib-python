Contribution guide
==================

👍🎉 Thanks a lot for considering contributing 🎉👍

We welcome and encourage contribution. There is many way to contribute: you can
write bug report, contribute code or documentation.
You can also go to the [bitcraze forum](https://forum.bitcraze.io) and help others.

## Reporting issues

When reporting issues the more information you can supply the better.
Since the lib runs on many different OSes, can connect to multiple versions of the Crazyflie and you could use our official releases or clone directly from Git, it can be hard to figure out what's happening.

 - **Information about the environment:**
   - What OS are your running on
   - What version of Python are you using
   - If relevant, what version of the Crazyflie firmware are you using
 - **How to reproduce the issue:** Step-by-step guide on how the issue can be reproduced (or at least how you reproduce it).
 Include everything you think might be useful, the more information the better.

## Improvements request and proposal

We and the community are continuously working to improve the lib.
Feel free to make an issue to request a new functionality.

## Contributing code/Pull-Request

We welcome code contribution, this can be done by starting a pull-request.

If the change is big, typically if the change span to more than one file, consider starting an issue first to discuss the improvement.
This will makes it much easier to make the change fit well into the lib.

There is some basic requirement for us to merge a pull request:
 - Describe the change
 - Refer to any issues it effects
 - Separate one pull request per functionality: if you start writing "and" in the feature description consider if it could be separated in two pull requests.
 - The pull request must pass the automated test (see test section bellow)

In your code:
- Don't include name, date or information about the change in the code. That's what Git is for.
- CamelCase classes, but not functions and variables
- Private variables and functions should start with _
- 4 spaces indentation
- When catching exceptions try to make it as specific as possible, it makes it harder for bugs to hide
- Short variable and function names are OK if the scope is small
- The code should pass flake8

### Run test

In order to run the tests you can run:
```
python tools/build/build
python3 tools/build/build
```
