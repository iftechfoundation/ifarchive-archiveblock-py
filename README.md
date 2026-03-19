# Service for restricting files

This tool is part of a system for restricting certain [IF Archive][ifarch] files from being served in the UK. It sucks that we have to do this, but we do. See discussion of the [UK Online Safety Act][ukosa].

[ifarch]: https://ifarchive.org/
[ukosa]: https://intfiction.org/t/uk-online-safety-act/75867

This plugin does not handle the geolocation check itself. The entire process looks like this:

- The `Index` files on the [Archive][ifarch] contain file tags like `safety: self-harm`.
- The [ifmap][] script reads these and constructs a text file which maps filenames to tag lists.
- This Python app loads the map file. When a request comes in for a tagged file, the browser is redirected to the `ukrestrict.ifarchive.org` domain.
- Cloudflare (the front-end for the public Archive service) does a geolocation check for any request that hits the `ukrestrict.ifarchive.org` domain. If the request comes from the UK, it is redirected to [https://ifarchive.org/misc/uk-block.html](https://ifarchive.org/misc/uk-block.html).

[ifmap]: https://github.com/iftechfoundation/ifarchive-ifmap-py

Why a Python WSGI app? The redirect step is a bit too messy to handle with standard Apache tools like [`mod_alias`][mod_alias] or [`mod_rewrite`][mod_rewrite]. The tricky requirements:

[mod_alias]: https://httpd.apache.org/docs/current/mod/mod_alias.html
[mod_rewrite]: https://httpd.apache.org/docs/current/mod/mod_rewrite.html

- The map file may be updated at any time. We must watch it and reload if the file timestamp changes. (This does not require an Apache restart.)
- We must be able to tag entire directories, since the tagging process is being worked on incrementally. (Many directories have not even been looked at yet.)
- All tagged files must get a `X-IFArchive-Safety` HTTP header listing the tags.
- Redirects must have the `X-IFArchive-Safety` header, and also `Access-Control-Allow-Origin: *`. (So that client-side services like [`iplayif.com`][iplayif.com] can detect them.)

[iplayif.com]: https://iplayif.com/

## Configuration

(TODO)

## The map file

The map file syntax can charitably be described as "dank". It's meant to be parsed by relatively simple code.

Map lines have the form:

```
PATHNAME [TAB] FLAGS:TAGS
```

For example:

```
/if-archive/games/foo.z5    u:visual-gore, self-harm
# Lines starting with a hash are comments
```

The separator is a tab character because filenames can contain spaces. If a filename contains a literal tab, I don't know what to tell you.

The *PATHNAME* will always start with `/if-archive`. It can look like:

```
# An exact filename
/if-archive/dir/filename.txt

# Tags will apply to all files in this directory
/if-archive/dir/*

# Tags will apply to all files in this directory *and* its subdirs
/if-archive/dir/**
```

Filename lines take precedence over directory lines; directory lines take precedence over subtree lines. This lets you build a tree of rules and exceptions in a sensible way.

The second part of the line is zero or more *FLAG* characters, followed by a (mandatory) colon, followed by a comma-separated list of tags (taken from the `safety: tags` metadata line). No spaces around the colon, please. If this segment is just `:`, then there are no tags and no flags. (Again, useful for creating exceptions to a directory rule.)

At present, the only meaningful *FLAG* character is `u`, meaning that the file must be restricted in the UK. If there is no `u` before the colon, the file has tags but none of the tags are UK-restricted.

(It's the [ifmap][] script's job to decide which tags are UK-restricted. This plugin just looks for the `u:` prefix.) (In the future we may need to restrict files in other regions, such as the EU.)


