# Why
We want distinct databases versioned by date rather than incremental updates
via `update_blastdb.pl`. Something like:
```
/home/jmbrown/blast
├── 2015-02-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
├── 2015-01-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
├── 2014-12-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
└── latest -> /home/jmbrown/blast/2015-02-01
```

# Requires
+ blastdbcheck
+ python
    + click
+ wget
+ md5sum
+ tar

# Running
```
$ blastdbget -d 16SMicrobial -d sts -d taxdb $HOME/blast
```

Output:
```
Info      : Using /home/jmbrown/blast as parent directory
Info      : Communicating with Blast server
Info      : Found 6 files matching databases: [16SMicrobial, sts, taxdb]
Info      : Downloading 6 files
Jobs Ran + Running  [####################################]  100%
Info      : Validating 3 archives
Jobs Ran + Running  [####################################]  100%
Info      : Extracting 3 archives
Jobs Ran + Running  [####################################]  100%
Info      : Cleaning up tar files
Info      : File permissions for /home/jmbrown/blast/2015-05-04 have been properly updated.
Writing messages to <stdout> at verbosity (Summary)
ISAM testing is ENABLED.
Legacy testing is DISABLED.
TaxID testing is DISABLED.
Testing 10 randomly sampled OIDs.

Finding database volumes.
Testing 2 volume(s).
 Result=SUCCESS. No errors reported for 2 volumes.
Testing 1 alias(es).
 Result=SUCCESS. No errors reported for 1 alias(es).
Complete  : Files available at /home/jmbrown/blast/latest
```

Note: If you want `blastdbcheck` to fully function, you should be grabbing
`-d taxdb`. If `blastdbcheck` fails, no symlink is created to "latest".

Not specifying `-d` will list Blast DBs that are available.

```
$ python blastdbget.py
Info      : Communicating with Blast server
Usage     : Set `-d` to an available database:
16SMicrobial
Representative_Genomes
cdd_delta
env_nr
env_nt
est
est_human
est_mouse
est_others
gss
gss_annot
htgs
human_genomic
...
```

# Results
```
/home/jmbrown/blast
├── 2015-05-04
│   ├── 16SMicrobial.nhr
│   ├── 16SMicrobial.nin
│   ├── 16SMicrobial.nnd
│   ├── 16SMicrobial.nni
│   ├── 16SMicrobial.nog
│   ├── 16SMicrobial.nsd
│   ├── 16SMicrobial.nsi
│   ├── 16SMicrobial.nsq
│   ├── sts.00.nhd
│   ├── sts.00.nhi
│   ├── sts.00.nhr
│   ├── sts.00.nin
│   ├── sts.00.nnd
│   ├── sts.00.nni
│   ├── sts.00.nog
│   ├── sts.00.nsd
│   ├── sts.00.nsi
│   ├── sts.00.nsq
│   ├── sts.nal
│   ├── taxdb.btd
│   └── taxdb.bti
└── latest -> /home/jmbrown/blast/2015-05-04
```

# Finish up
Set `BLASTDB` to `latest`.
```
export BLASTDB=/home/jmbrown/blast/latest
```

We do monthly updates:
```
0 0 1 * * blastdbget -t 8 -d nr -d nt -d taxdb /mnt/databases/NCBI/blast
```
