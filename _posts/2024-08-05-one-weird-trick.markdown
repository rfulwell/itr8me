---
layout: post
title:  "One Weird Trick to Become a 10x Dev!"
date:   2024-08-05 12:57:48 -0700
categories: dev
---
# Not a trick - a truth: communication is the key.

In a time of Large Language Models (LLMs) that can write, test, and debug functional code in many computer programming languages one thing is more clear than ever: churning out a lot of code is not what makes you a great dev! If the code works and even has tests to verify it, don’t try to compete with machines on volume of output.

![a woman is running on a treadmill](https://images.unsplash.com/photo-1638183395699-2c0db5b6afbb?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwzMDAzMzh8MHwxfHNlYXJjaHwyfHx0cmVhZG1pbGx8ZW58MHx8fHwxNjgyMjk0Mjk3&ixlib=rb-4.0.3&q=80&w=1080 "Photo by Intenza Fitness on Unsplash")

So what separates you from the latest code generation tool?

The answer is a cliché: communication.

Whether you acknowledge it or not, as a dev 90% of your job is communication. This is not a new idea but in this post I’ll highlight some specific forms of communication that get overlooked. Hopefully you’ll come away with a fresh perspective on how to level up your work with small communication enhancements.

# But I’m an introvert!
This is not about giving a great TED talk or being the life of the party. It comes down to making effective use of the best tools you have available (a theme I’ll return to in other posts). Obviously communication is a huge topic so in this post let’s briefly drill into specific examples:

- Tech designs
- Code reviews
- Work tracking (e.g. Jira issues)
- Slack (or Teams or …)
- Code + comments + commit messages

Each of these bullets is a big subject so I’m going to cherry pick.

## Tech designs
![world map poster](https://images.unsplash.com/photo-1519885277449-12eee5564d68?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzMDAzMzh8MHwxfHNlYXJjaHwxM3x8bWFwfGVufDB8fHx8MTY4NTgzNjQ3NHww&ixlib=rb-4.0.3&q=80&w=1080 "Photo by Tabea Schimpf on Unsplash")

### Explore the problem
Some shops don’t do formal tech designs and others write extensive specification documents up front before a single line of code is written. The context matters but at the end of the day a tech design is an attempt to explore the problem space before we get to the expensive work of programming. It may feel like wasted time writing a document when you could be writing code but problems are easier and cheaper to fix when we find them early in the dev cycle.

### Key communication:
Find a solution that fits the current business requirements but can evolve as requirements change. The tech design should clearly summarize the options that were considered, with linked references for folks who want to dig into the details. It is important to briefly cover the options that were _not_ selected and why.

This leads to another important aspect of the tech design - the recommendation. A big part of the value of the tech design is the recommendation. This is where the developer’s experience, research and communication skills come together to present the path forward. The team may agree and move forward as-is or discuss it and go another way but a cogent recommendation should power that conversation.

## Code reviews
![person using laptop](https://images.unsplash.com/photo-1516321318423-f06f85e504b3?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzMDAzMzh8MHwxfHNlYXJjaHwxM3x8ZmVlZGJhY2t8ZW58MHx8fHwxNjg1ODM2Njk4fDA&ixlib=rb-4.0.3&q=80&w=1080 "Photo by John Schnobrich on Unsplash")

### Context is key
Is this an early “WIP” draft of the solution or are we fixing the last few showstoppers before the product ships out to customers? Understanding the goal of a change is important to providing meaningful feedback. For example, structural changes to the approach may be appropriate early on in a project but to the code author, sweeping changes will sound like an annoying distraction when they are driving towards a deadline!

### Key communication:
There’s a lot of wonderful advice about code reviews but the one message I’ll emphasize is that this is another opportunity for learning and cross-training. Particularly when the author or the reviewer is more or less experienced, the code review is a place for invaluable coaching and knowledge transfer. Professional developers should welcome all code review comments as useful feedback. This is an opportunity to learn and improve the quality of your work. Even a misunderstanding along the way can show that there is room for the code, comments or the change description to be better.

## Work tracking
![pencil on opened notebook](https://images.unsplash.com/photo-1511871893393-82e9c16b81e3?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzMDAzMzh8MHwxfHNlYXJjaHwxfHxkaWFyeXxlbnwwfHx8fDE2ODU4MzY3OTV8MA&ixlib=rb-4.0.3&q=80&w=1080 "Photo by JESHOOTS.COM on Unsplash")

### For the record (maybe for future you!)
Jira issues aren’t just for PMs! Well written change requests clearly lay out motivation for the task and the desired results in the form of acceptance criteria. Moreover, when you add comments to record the research you do or the problems you encounter, you create documentation that will help the next person understand what’s going on with the issue if it gets handed off or postponed for some reason. There’s a good chance that you may end up putting the task on the back burner and then weeks or months later when you come back to it, your notes in the Jira issue will save you time when you try to pick up where you left off.

### Key communication:
A good description is useful but much of the value of a Jira issue is in updated comments with links, screenshots or other data that provide the supporting info needed to understand the development of a solution. It works well to add comments to active issues daily as a running log of what is learned.

## Slack
![silhouette of woman holding rectangular board](https://images.unsplash.com/photo-1602189156324-4c5c6c2c02b3?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzMDAzMzh8MHwxfHNlYXJjaHwxfHxhbm5vdW5jZXxlbnwwfHx8fDE2ODU4MzY4Mzh8MA&ixlib=rb-4.0.3&q=80&w=1080 "Photo by Patrick Fore on Unsplash")

### More is more
Have you ever posted to Slack and been super frustrated when there is no response?

In general, err on the side of more information and transparency. This includes feedback to Slack posts. If you see an FYI post that is somewhat useful or even might be useful in the future, take two seconds to throw an emoji reaction on there! This simple feedback is a powerful message that the information was received.

As an organization grows it becomes increasingly challenging to keep everyone on the same page and Slack provides a number of ways to meet that challenge:

- emoji reactions to signal receipt of information (good, bad or indifferent - send it!)
- pinned posts - mark salient info for yourself or for newbies onboarding later
- create a thread - avoid noise in the main channel but preserve details (with time stamps!) for later reference or lurkers following along
- [DRY](https://en.wikipedia.org/wiki/Don't_repeat_yourself) - forward posts from public channels instead of copy/pasting in order to keep the discussion in one place
- use channels instead of DMs - err on the side of more public communication* to facilitate involving more folks in the conversation later, if needed
- use @mentions for groups rather than individuals where possible - ideally your teams have aliases such that you don’t need a specific person to respond

*Respect privacy concerns when necessary of course but unless there’s a reason to keep something private, I like to default to openness.

### Key communication:
Slack has a lot of tools to help your organization transfer information from individuals to groups and across time from right now to some time in the future when you or someone you may never meet is desperately in need of that information. Use those tools effectively and the team moves forward faster and more confidently together.

There’s a lot more to say about Slack. I was initially skeptical of Huddles but now I use them routinely for ad hoc conversations and screen sharing. Now I am intrigued by their new Canvas feature as a competitor to Confluence or simple Google Docs but I’ll cover that in another post.

## Code and comments
![black flat screen computer monitor](https://images.unsplash.com/photo-1606606767399-01e271823a2e?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzMDAzMzh8MHwxfHNlYXJjaHw3fHxtYXRyaXh8ZW58MHx8fHwxNjg1ODM2ODc3fDA&ixlib=rb-4.0.3&q=80&w=1080 "Photo by Compare Fibre on Unsplash")

### The hard part is making it seem obvious
It is well understood that programmers spend far more time reading code than they do writing it. The subtext here is that a machine (an interpreter executable, a compiler, etc.) does not care how complicated your code is as long as it fits the constraints of the system. On the other hand, a human who must understand that code will spend more time and energy (and frustration) trying to grok code that is complex, crufty or “clever.”

In this context, the primary goal should be to help that future human reader come to a correct understanding as quickly and easily as possible. This is another area with a vast amount of commentary and advice from folks far more qualified than I am but I do want to emphasize that good code is a concise, clear communication from the code author to the (human) code reader. Obvious code is surprisingly challenging to create but the rewards of that effort compound over time.

There are multiple layers of communication available here. The code should be as simple as possible ([but no simpler!](https://quoteinvestigator.com/2011/05/13/einstein-simple/) 😉). In places where there is still ambiguity in the code, a brief comment can be invaluable. If there are outright gotchas or confusing details in the data, perhaps a longer comment is needed. Where you did a lot of research into other solutions or maybe went down an unproductive path for some reason, save the next person that trouble by documenting it in the commit comments or the change description!

A quick note on commit comments: please make them succinct but meaningful. Tools like [blame](https://www.cloudbees.com/blog/git-blame-explained) and `git log` are far more helpful when the content they surface is thoughtfully created. Hopefully your team is using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary)!

### Key communication:
Consider the human readers more than the machine readers of your code. As [a wise man once said](https://www.defprogramming.com/quotes-by/martin-golding/):

> Always code as if the guy who ends up maintaining your code will be a violent psychopath who knows where you live.
-Martin Golding

# Summing up
Believe it or not, the most valuable software developers are masters of communication and empathy. This has little to do with how gregarious you are! The genius lies in making complex solutions seem obvious by decomposing the problem into code which speaks for itself along with judicious use of comments and commit messages.

Finally, unless you’re working on a solo project, you differentiate yourself from average devs by making effective use of the available communication tools. Consider your audience, give good feedback (even just one click on an emoji!) and be kind. 🙂
