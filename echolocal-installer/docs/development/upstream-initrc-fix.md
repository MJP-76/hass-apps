# Upstream fix: `initRC` aborts on a non-matching glob

Upstream issue: [ygelfand/echolocal#94](https://github.com/ygelfand/echolocal/issues/94)

## The bug

`internal/host/installer/system.go`, `initRC`:

```go
func (r *run) initRC(at string) ([]string, error) {
	globs := []string{at + "/system/etc/init/*.rc", at + "/vendor/etc/init/*.rc"}
	if r.board().SystemAsRoot {
		globs = append([]string{at + "/*.rc"}, globs...)
	}

	found, err := r.d.Shell("ls " + strings.Join(globs, " ") + " 2>/dev/null")
	if err != nil {
		return nil, fmt.Errorf("listing the init rc files: %w", err)
	}
	return strings.Fields(found), nil
}
```

`Device.Shell` treats any non-zero exit as an error. `ls` exits non-zero when a glob matches
nothing, which is a legitimate outcome here — a directory with no rc files contributes no
matches, it is not a failure. On a Fire OS 6 device where `/system_root/vendor` is an absolute
symlink to `/system/vendor`, and TWRP's `/system` has no `vendor/etc/init`, every candidate glob
can miss at once, so `ls` exits 1 and the install aborts before it ever reaches the overwrite
and Wi-Fi steps.

## The fix

Use `ShellCode`, which returns the exit status rather than raising on a non-zero one, and
ignore it. A missing match simply yields no paths.

```diff
--- a/internal/host/installer/system.go
+++ b/internal/host/installer/system.go
@@ -60,8 +60,10 @@ func (r *run) initRC(at string) ([]string, error) {
 		globs = append([]string{at + "/*.rc"}, globs...)
 	}
 
-	found, err := r.d.Shell("ls " + strings.Join(globs, " ") + " 2>/dev/null")
-	if err != nil {
+	// ls exits non-zero when a glob matches nothing; that is not an error, it just means the
+	// directory contributed no rc files. Read the exit status instead of treating it as fatal.
+	found, _, err := r.d.ShellCode("ls " + strings.Join(globs, " ") + " 2>/dev/null")
+	if err != nil {
 		return nil, fmt.Errorf("listing the init rc files: %w", err)
 	}
 	return strings.Fields(found), nil
```

`ShellCode` already exists and is used elsewhere:

```go
func (d *Device) ShellCode(cmd string) (string, int, error) {
	return d.shell(cmd)
}
```

The same pattern is worth auditing in every other caller that shells out to `ls`, `test`, `grep`
and friends and treats a non-zero exit as fatal.

## Draft comment for issue #94

> The `initRC` failure reproduced here is a glob that matches nothing being treated as fatal.
> `Device.Shell` fails on any non-zero exit, and `ls` exits 1 when a glob has no match —
> which is exactly what happens when `/system_root/vendor` is an absolute symlink to
> `/system/vendor` and TWRP's `/system` has no `vendor/etc/init`.
>
> The one-line fix is to read the exit status instead of raising on it:
>
> ```go
> found, _, err := r.d.ShellCode("ls " + strings.Join(globs, " ") + " 2>/dev/null")
> if err != nil {
>     return nil, fmt.Errorf("listing the init rc files: %w", err)
> }
> ```
>
> `ls` printing nothing and exiting non-zero is a valid empty result here, so the `err` from
> `ShellCode` only needs to cover the adb failing outright. As of today `main`
> (`7ee99f263d…`) and the 0.0.8 release on the download page both still contain the
> `Shell`-based version, so the "fixed in the latest dev release" reply on this issue is not
> something a user can actually download yet. Happy to send this as a PR if useful.

## Remove the add-on workaround when…

- A release is cut that contains the `ShellCode` change, **and**
- `echolocal-installer/config.yaml` pins `echoctl_version` to it.

Then delete `apply_vendor_workaround` from `app/server.py`, drop the workaround note from the
README, and close the **Soon** item in `TODO.md`.
