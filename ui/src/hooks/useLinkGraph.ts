/**
 * useLinkGraph — D3 force simulation dengan RAF-based rendering.
 * Mengembalikan nodesRef (mutable, diupdate oleh sim) dan renderVersion
 * untuk trigger React re-render hanya saat dibutuhkan (~60fps).
 */
import { useEffect, useRef, useState, useMemo } from 'react'
import * as d3 from 'd3'
import type { Profil, Pertemanan, Postingan } from '../types'

export type NodaTipe = 'profil' | 'postingan' | 'balasan'

export interface Noda extends d3.SimulationNodeDatum {
  id: string
  tipe: NodaTipe
  label: string
  avatar?: string
  platform?: string
  profil_id?: string
  klaster?: string
}

export interface Edge extends d3.SimulationLinkDatum<Noda> {
  id: string
  tipe: 'pertemanan' | 'postingan' | 'balasan'
  kekuatan?: number
}

type Props = {
  profil: Profil[]
  pertemanan: Pertemanan[]
  postingan: Postingan[]
  showPertemanan: boolean
  showPostingan: boolean
  showBalasan: boolean
}

export function useLinkGraph({
  profil, pertemanan, postingan,
  showPertemanan, showPostingan, showBalasan,
}: Props) {
  // nodesRef: posisi diupdate langsung oleh sim (tidak melalui React state)
  const nodesRef = useRef<Noda[]>([])
  const edgesRef = useRef<Edge[]>([])
  const simRef   = useRef<d3.Simulation<Noda, Edge> | null>(null)
  const rafRef   = useRef<number>(0)
  // renderVersion: trigger React re-render via RAF (max ~60fps)
  const [renderVersion, setRenderVersion] = useState(0)

  const { rawNodes, rawEdges } = useMemo(() => {
    const nodaMap = new Map<string, Noda>()

    profil.forEach(p => nodaMap.set(p.id_profil, {
      id: p.id_profil,
      tipe: 'profil',
      label: p.nama_lengkap,
      avatar: p.url_avatar,
      klaster: p.id_klaster[0],
    }))

    const rawEdges: Edge[] = []

    if (showPertemanan) {
      pertemanan.forEach(pt => {
        if (nodaMap.has(pt.profil_a) && nodaMap.has(pt.profil_b)) {
          rawEdges.push({
            id: pt.id_pertemanan,
            source: pt.profil_a,
            target: pt.profil_b,
            tipe: 'pertemanan',
            kekuatan: pt.kekuatan,
          })
        }
      })
    }

    if (showPostingan) {
      postingan.forEach(ps => {
        if (!nodaMap.has(ps.id_posting)) {
          nodaMap.set(ps.id_posting, {
            id: ps.id_posting,
            tipe: 'postingan',
            label: ps.konten.slice(0, 40),
            platform: ps.platform,
            profil_id: ps.id_profil,
          })
        }
        if (nodaMap.has(ps.id_profil)) {
          rawEdges.push({
            id: `e-${ps.id_posting}`,
            source: ps.id_profil,
            target: ps.id_posting,
            tipe: 'postingan',
          })
        }
      })
    }

    if (showBalasan) {
      postingan
        .filter(ps => ps.balas_ke_id_posting && nodaMap.has(ps.id_posting) && nodaMap.has(ps.balas_ke_id_posting))
        .forEach(ps => {
          rawEdges.push({
            id: `r-${ps.id_posting}`,
            source: ps.id_posting,
            target: ps.balas_ke_id_posting!,
            tipe: 'balasan',
          })
        })
    }

    return { rawNodes: Array.from(nodaMap.values()), rawEdges }
  }, [profil, pertemanan, postingan, showPertemanan, showPostingan, showBalasan])

  useEffect(() => {
    if (rawNodes.length === 0) {
      nodesRef.current = []
      edgesRef.current = []
      setRenderVersion(v => v + 1)
      return
    }

    // Posisi awal menyebar — hindari semua tumpuk di (0,0)
    rawNodes.forEach(n => {
      if (n.x === undefined) {
        n.x = (Math.random() - 0.5) * 600
        n.y = (Math.random() - 0.5) * 400
      }
    })

    nodesRef.current = rawNodes
    edgesRef.current = rawEdges

    const sim = d3.forceSimulation<Noda>(rawNodes)
      .force('link', d3.forceLink<Noda, Edge>(rawEdges)
        .id(d => d.id)
        .distance(d => d.tipe === 'pertemanan' ? 90 : 35)
        .strength(d => d.tipe === 'pertemanan' ? 0.5 : 0.25)
      )
      .force('charge', d3.forceManyBody<Noda>().strength(d => d.tipe === 'profil' ? -220 : -50))
      .force('collision', d3.forceCollide<Noda>().radius(d => d.tipe === 'profil' ? 24 : 9).iterations(2))
      .force('center', d3.forceCenter(0, 0).strength(0.04))
      .alphaDecay(0.025)
      .velocityDecay(0.4)
      // Tick handler hanya update ref, tidak setState
      .on('tick', () => {
        nodesRef.current = rawNodes
        edgesRef.current = rawEdges
      })

    simRef.current = sim

    // RAF loop — re-render React hanya saat sim aktif, max 60fps
    let active = true
    function rafLoop() {
      if (!active) return
      if (sim.alpha() > sim.alphaMin()) {
        setRenderVersion(v => v + 1)
        rafRef.current = requestAnimationFrame(rafLoop)
      } else {
        // Sim sudah settled — satu re-render terakhir
        setRenderVersion(v => v + 1)
      }
    }
    rafRef.current = requestAnimationFrame(rafLoop)

    return () => {
      active = false
      sim.stop()
      cancelAnimationFrame(rafRef.current)
    }
  }, [rawNodes, rawEdges])

  return { nodesRef, edgesRef, renderVersion, simRef }
}
