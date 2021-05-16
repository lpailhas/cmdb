This repository contains the configuration management system for Blade
Network Team. It contains the base of truth in `data/`. Jerikan is the
piece of software generating configuration files from data and
templates in `templates/`. It uses the list of devices in
`devices.yaml` and build a scope for each device using
`classifier.yaml`. Ansible playbooks to deploy generated files are in
`ansible/`.

More details on use and rationale are available in a [blog post][].

[blog post]: https://vincent.bernat.ch/en/blog/2021-cmdb-network "Jerikan: a configuration management system for network teams"

# Get started

## Setup

You may need to authenticate to Gitlab with a [personal access
token][] as password (scope is `read_registry`) using the following
command:

```console
$ docker login registry.gitlab.com
```

[personal access token]: https://gitlab.com/profile/personal_access_tokens

On first invocation, `docker-compose` will automatically build and
fetch the images. To force a rebuild of some of the images, use:

```console
$ docker image rm --no-prune cmdb_jerikan:latest cmdb_ansible:latest
```

## Build templates

```console
$ rm -rf output
$ ./run-jerikan build
```

To limit to a few devices:

```console
$ ./run-jerikan build --limit=gateway\?.ussfo03.blade-group.net,none
```

## Get the scope of a device

To get the scope of a device (and also the search paths for YAML files):

```console
$ ./run-jerikan -s scope to1-p2.ussfo03.blade-group.net
# Scope:
continent: us
environment: prod
groups:
- tor
- tor-bgp
- tor-bgp-compute
host: to1-p2.ussfo03
location: ussfo03
member: '1'
model: wedge100
os: cumulus
pod: '2'
shorthost: to1-p2

# Search paths:
# (host/to1-p2.ussfo03)
# (host/prod.ussfo03/to1-p2)
#  host/ussfo03/to1-p2
# (groups/tor-bgp-compute-cumulus-wedge100-member1)
# (groups/tor-bgp-cumulus-wedge100-member1)
# (groups/tor-cumulus-wedge100-member1)
# (groups/tor-bgp-compute-member1)
# (groups/tor-bgp-member1)
# (groups/tor-member1)
# (groups/tor-bgp-compute-prod.ussfo03-pod2)
# (groups/tor-bgp-prod.ussfo03-pod2)
# (groups/tor-prod.ussfo03-pod2)
# (groups/tor-bgp-compute-ussfo03-pod2)
# (groups/tor-bgp-ussfo03-pod2)
# (groups/tor-ussfo03-pod2)
# (groups/tor-bgp-compute-prod.ussfo03)
# (groups/tor-bgp-prod.ussfo03)
# (groups/tor-prod.ussfo03)
#  groups/tor-bgp-compute-ussfo03
# (groups/tor-bgp-ussfo03)
# (groups/tor-ussfo03)
# (groups/tor-bgp-compute-us)
# (groups/tor-bgp-us)
# (groups/tor-us)
# (groups/tor-bgp-compute-cumulus-wedge100)
#  groups/tor-bgp-cumulus-wedge100
# (groups/tor-cumulus-wedge100)
#  groups/tor-bgp-compute
#  groups/tor-bgp
# (groups/tor)
# (groups/prod.ussfo03)
#  groups/ussfo03
#  os/cumulus-wedge100
# (os/cumulus-ussfo03)
#  os/cumulus
#  common
```

## Key lookup for a device

```console
$ ./run-jerikan -s lookup to1-p2.ussfo03.blade-group.net system netbox
manufacturer: Edge-Core
model: Wedge 100-32X
role: net_tor_gpu_switch
```

# Run Ansible

The main playbook is in `ansible/playbooks/site.yaml`. It should
mostly only contains mapping between group of devices and roles. The
inventory is generated by the `none` special device. To deploy the
files generated from GitLab CI with Ansible, use:

```
./run-ansible-gitlab playbooks/site.yaml --diff --check --limit=gateway\?.ussfo03.blade-group.net
```

A limit has to be provided. Possible patterns could be:

- `--limit='gateway1.ussfo03.blade-group.net'` to limit to a specific host
- `--limit='environment-prod:&adm-gateway'` to limit to a specific group
- `--limit='environment-prod:&location-ussfo03:&tor:&member-1'` to limit to a subset of a group in a location

Some tasks are also tagged to only apply a subset of configuration.
Notably:

- `-t base` will only apply base modifications (NTP, syslog, users, passwords...)
- `-t irr` will only apply IRR updates
- `-t all,reboot` will authorize a reboot of a device if needed

Host `none` also comes with additional tags to limit its scope. They
all start with `deploy:`.

`./run-ansible-gitlab` will run against the data generated by GitLab
CI for the current master. If you prefer to generate the data locally
with Jerikan, use `./run-ansible` instead. From time to time, you can
cleanup fetched configurations:

```console
$ docker image ls -q registry.gitlab.com/blade-group/infra/network/cmdb:outputs-\* | xargs docker image rm
```

Some tasks may need an access to Vault. Go to Vault, authenticate
and get your token using the upper right menu with "Copy token". Then,
use the following command before invoking `./run-ansible-gitlab` or
`./run-ansible` (extra space before `export` ensures the token doesn't
end in your history):

```console
$  export VAULT_TOKEN=joi75209gdfukjlfg87gngf
```

## Recipes

### Deploy base configuration on JunOS

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit=os-junos -t base --diff --check
```

### Deploy complete configuration on edge1.* for JunOS:

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit='os-junos:&member-1' -t irr --diff --check
$ ./run-ansible-gitlab playbooks/site.yaml --limit='os-junos:&member-1' -t irr
$ ./run-ansible-gitlab playbooks/site.yaml --limit='os-junos:&member-1' --diff --check
$ ./run-ansible-gitlab playbooks/site.yaml --limit='os-junos:&member-1'
```

To make it easier to see the differences, we first apply only changes
for IRR (which may output large diffs), and then the complete
configuration.

### Deploy configuration on nat1.dfr1.blade-group.net

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit=nat1.dfr1.blade-group.net -t all,reboot --diff --check
```

### Deploy EVPN configuration on lab

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit='environment-lab:&location-pa1' --diff --check
```

### Update DNS records (Route53, PowerDNS, RIPE, ARIN)

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit=none -t deploy:dns -v --check
```

### Update IRR records (ARIN, APNIC, RIPE)

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit=none -t deploy:irr -v --check
```

### Synchronize Netbox

```console
$ ./run-ansible-gitlab playbooks/site.yaml --limit=none -t deploy:netbox -v --diff --check
```

### Use another base than master for ./run-ansible-gitlab

By default, `./run-ansible-gitlab` will use the output compiled from
master by GitLab. If needed, this is possible use an older version of
master or the result of a merge request. For this, you need to
retrieve the SHA of the commit to use as a base.

For older versions of master, the [commit
history](https://gitlab.com/blade-group/infra/network/cmdb/-/commits/master)
as the information. Use the clipboard icon to retrieve the full SHA.
Only the commits with a green checkmark will work. For MR, you can get
the same information from the "Commits" tab. Only the top-most commit
will work.

Then, use the following command:

```console
$ SHA=87bf08251961d1bb783cfe0274f7e37a3d4ed175 ./run-ansible-gitlab playbooks/site.yaml --limit=none -t deploy:netbox --diff --check
```

If you have a merge request you want to apply, switch to your branch and use:

```console
$ SHA=$(git rev-parse HEAD) ./run-ansible-gitlab ...
```

### Get facts from a device
Sometimes you may need to get the whole facts list from a specific device.
It can be retrieved by using:

```
./run-ansible playbooks/facts.yaml --limit="spine1-n1.sk1.*"
```

# Coding

## Namespaces

 - `system`: for system-related stuff (accounts, syslog servers)
 - `topology`: for topology-related stuff (interfaces, IP, neighbors)
 - `bgp`: for BGP-related stuff (peerings, transits)
 - `build`: for build-system-related stuff (templates, scripts)
 - `apps`: for apps-related stuff (applications vars)

## Templates

### Functions

There are are several additional functions:

 - `devices()` will return the list of devices matching the set of
   conditions provided as arguments using the scope. For example,
   `devices("location==ch1", "groups==tor-evpn")` will return the list
   of devices in Chicago behaving as a ToR switch with EVPN enabled.
   Accepted operators are `==` and `!=`. You can also omit the
   operator if you want the specified value to be equal to the one in
   the local scope. For example, `devices("environment", "location",
   "groups==tor-evpn")` is the canonical way to get ToR devices on the
   same environment/location than the current device.

 - `lookup()` will do a key lookup. It takes the namespace, the key
   and optionally, a device name. If no device name, the current
   device is assumed.

 - `scope()` will provide the scope of the provided device.

 - `bgpq3()` is building a prefix-list with bgpq3.

 - `peeringdb()` fetches information about the provided AS from
   PeeringDB.

If the namespace of the lookup function is `bgptth`, the value is
computed for use with "BGP-to-the-host" design. The expected key is
`local:port remote:port` with the following shortcuts allowed:

 - `remote:port`, `local` is assumed to be the current device or the
   device specified as a third argument in `lookup()` and the local
   port is assumed to not be needed;
 - `local remote:port`, the local port is assumed to not be needed;
 - `:port remote`, `local` is assumed to be the current device or the
   device specified as a third argument in `lookup()` and the remote
   port is assumed to not be needed;
 - an empty key will return only information about the local ASN;

```console
$ ./run-jerikan -s lookup to1-sp7.ams1.blade-group.net bgptth ":xe-0/0/6 sh-172-24-67-15"
asn: 4203981007
private: 10.67.206.44/31
provisioning: 10.135.156.89/30
public: 100.67.206.44/31
$ ./run-jerikan -s lookup to1-sp7.ams1.blade-group.net bgptth ""
asn: 4203981007
$ ./run-jerikan -s lookup to1-sp7.ams1.blade-group.net bgptth "spine1-storage-n1:et-0/0/4"
asn: 4203981007
private: 10.67.239.9/31
public: 100.67.239.9/31
```

### Filters

In addition to [standard Jinja2 filters][], Jerikan adds its own
filters:

 - `ipv` returns the version of an address,
 - `ippeer` returns the peer address of a /31 or /30,
 - `ipoffset` computes an IP address as an offset from a provided base address,
 - `torange` converts a human-readable range like `4-10` to a list,
 - `tolist` converts anything not a list to a list of a single element
   (and does nothing if you already provide a list),
 - `slugify` transforms a string to only use alphanumeric characters,

The following [filters from Ansible][] are also exposed:

 - `regex_search`
 - `regex_replace`
 - `b64decode`
 - `cidr_merge`
 - `ipaddr`
 - `ipmath`
 - `ipv4` and `ipv6`
 - `hwaddr`
 - `hash`
 - `password_hash`
 - `to_yaml`, `to_nice_yaml` and `to_json`

[standard Jinja2 filters]: https://jinja.palletsprojects.com/en/2.11.x/templates/#builtin-filters
[filters from Ansible]: https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html

### Key-value store

It is possible to use a template as a value in the key-value store.
You need to prefix the value with `~`. This should not be abused but
this can be used to have a generic configuration for a type of
equipment with values specific for each equipment. For example:

```yaml
# In common YAML
interfaces:
  "~bond0.{{ lookup('topology', 'vlans')['nat-spine1'] }}":
    address: "~{{ lookup('topology', 'addresses').spine1 }}"
  "~bond0.{{ lookup('topology', 'vlans')['nat-spine2'] }}":
    address: "~{{ lookup('topology', 'addresses').spine2 }}"

# In nat1 YAML
nat-address-1: 185.231.156.1/31
nat-address-2: 185.231.156.3/31

# In nat2 YAML
nat-address-1: 185.231.156.5/31
nat-address-2: 185.231.156.7/31
```

This also works for structured data:

```yaml
# In groups/adm-gateway-l3/topology.yaml
interface-rescue:
  address: "~{{ lookup('topology', 'addresses').rescue }}"
  up:
    - "~ip route add default via {{ lookup('topology', 'addresses').rescue|ipaddr('first_usable') }} metric 4278198271 table public"
    - "~ip route add default via {{ lookup('topology', 'addresses').rescue|ipaddr('first_usable') }} table rescue"
    - "~ip rule add from {{ lookup('topology', 'addresses').rescue|ipaddr('address') }} table rescue priority 10"

# In groups/adm-gateway-sk1/topology.yaml
interfaces:
  ens1f0: "~{{ lookup('topology', 'interface-rescue') }}"
```

```console
$ ./run-jerikan -s lookup gateway1.sk1.blade-group.net topology interfaces
ens1f0:
  address: 121.78.242.10/29
  up:
  - ip route add default via 121.78.242.9 metric 4278198271 table public
  - ip route add default via 121.78.242.9 table rescue
  - ip rule add from 121.78.242.10 table rescue priority 10
lo:1:
[...]
```

There is also a special notation for a list when you want to get the
IPv6 address from an IPv4 address:

```yaml
addresses:
  loopback:
    - 103.153.6.2/24
    - ~^ip6
```

This will be translated to:

```yaml
addresses:
  loopback:
    - 103.153.6.2/24
    - 2406:3bc0:100:b1:a:de:103.153.6.2/120
```

This requires `base-public-6` to be defined in `topology.yaml`.

## Checks

Check scripts are executed from the main directory and are provided
with the name of the device as an additional argument. We store them
in `checks/`.

During development, you may want to speedup template generations by
skipping checks with `--skip-checks` option.


## Best practices

- Never use underscore in key names in YAML files.
- Use dotted notation if possible in Jinja2.
- Use a space after `{%` and `{{`.
- Use a space before `%}` and `}}`.
- Use a space after comma in function calls.
- Use spaces around `=` on assignment.
